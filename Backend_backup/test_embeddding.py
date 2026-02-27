"""
Generate movie embeddings from movies_dataset_final.json and upsert to PostgreSQL.

This script intentionally does not modify existing project files.
It uses Bedrock (LLM + embedding) via functions defined in:
ml/model_sample/analysis/embedding.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import select

from db import SessionLocal
from models import Movie, MovieVector
from ml.model_sample.analysis import embedding as emb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate embeddings with Bedrock and upsert into movie_vectors."
    )
    parser.add_argument(
        "--profiles-input",
        default=None,
        help="Existing profiles JSON path. If set, skip Bedrock generation and upsert this file directly.",
    )
    parser.add_argument(
        "--movies",
        default="ml/data/movies_dataset_final.json",
        help="Input movie dataset JSON path.",
    )
    parser.add_argument(
        "--taxonomy",
        default="ml/data/emotion_tag.json",
        help="Emotion taxonomy JSON path.",
    )
    parser.add_argument(
        "--output",
        default="profiles.json",
        help="Output JSON path for generated profiles (profiles_sample.json format).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of movies to process.",
    )
    parser.add_argument(
        "--movie-id",
        type=int,
        default=None,
        help="Process only one movie id.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run generation and validation without DB commit.",
    )
    parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help="Allow local fallback scoring if Bedrock call fails.",
    )
    return parser.parse_args()


def load_json(path: str) -> Any:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_profile_strict(
    movie: dict[str, Any],
    taxonomy: dict[str, Any],
    bedrock_client: Any,
    allow_fallback: bool,
) -> dict[str, Any]:
    text = emb.movie_text(movie)

    llm_analysis = emb.analyze_with_llm(text, taxonomy, bedrock_client)
    if llm_analysis is None and not allow_fallback:
        raise RuntimeError(
            f"LLM analysis failed for movie_id={movie.get('id')} title={movie.get('title')}"
        )

    if llm_analysis is None:
        emotion_tags = taxonomy.get("emotion", {}).get("tags", [])
        narrative_tags = taxonomy.get("story_flow", {}).get("tags", [])
        direction_tags = taxonomy.get("direction_mood", {}).get("tags", [])
        char_tags = taxonomy.get("character_relationship", {}).get("tags", [])
        profile = {
            "movie_id": movie.get("id"),
            "title": movie.get("title"),
            "emotion_scores": emb.score_tags(text, emotion_tags),
            "narrative_traits": emb.score_tags(text, narrative_tags),
            "direction_mood": emb.score_tags(text, direction_tags),
            "character_relationship": emb.score_tags(text, char_tags),
            "ending_preference": {
                "happy": emb.stable_score(text, "ending_happy"),
                "open": emb.stable_score(text, "ending_open"),
                "bittersweet": emb.stable_score(text, "ending_bittersweet"),
            },
        }
    else:
        profile = {
            "movie_id": movie.get("id"),
            "title": movie.get("title"),
            "emotion_scores": llm_analysis["emotion"],
            "narrative_traits": llm_analysis["story_flow"],
            "direction_mood": llm_analysis["direction_mood"],
            "character_relationship": llm_analysis["character_relationship"],
            "ending_preference": llm_analysis["ending_preference"],
        }
        # Keep optional extra metadata from embedding.py output in JSON artifacts.
        if isinstance(llm_analysis.get("embedding_description"), str):
            profile["embedding_description"] = llm_analysis["embedding_description"]

    emb_txt = emb.embedding_text(profile)
    vector = emb.embedding_vector(emb_txt, bedrock_client)
    if (not vector) and (not allow_fallback):
        raise RuntimeError(
            f"Embedding generation failed for movie_id={movie.get('id')} title={movie.get('title')}"
        )

    profile["embedding"] = vector or []
    profile["embedding_text"] = emb_txt
    return profile


def normalize_profile_for_db(profile: dict[str, Any]) -> dict[str, Any]:
    movie_id = profile.get("movie_id")
    if movie_id is None:
        raise ValueError("Profile missing movie_id")

    try:
        movie_id = int(movie_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid movie_id: {movie_id}") from exc

    embedding_vector = profile.get("embedding")
    if embedding_vector is None:
        embedding_vector = profile.get("embedding_vector", [])

    if not isinstance(embedding_vector, list):
        embedding_vector = []

    return {
        "movie_id": movie_id,
        "emotion_scores": profile.get("emotion_scores") or {},
        "narrative_traits": profile.get("narrative_traits") or {},
        "ending_preference": profile.get("ending_preference") or {},
        "direction_mood": profile.get("direction_mood") or {},
        "character_relationship": profile.get("character_relationship") or {},
        "embedding_text": profile.get("embedding_text"),
        "embedding_vector": embedding_vector,
    }


def main() -> None:
    args = parse_args()
    load_dotenv(".env")

    profiles: list[dict[str, Any]] = []
    fixed_updated_at = datetime(2026, 2, 19, 0, 0, 0, tzinfo=timezone.utc)

    db = SessionLocal()
    inserted = 0
    updated = 0
    skipped_missing_movie = 0
    try:
        if args.profiles_input:
            raw_profiles = load_json(args.profiles_input)
            if not isinstance(raw_profiles, list):
                raise ValueError("profiles-input JSON must be a list.")
            total = len(raw_profiles)
            for idx, p in enumerate(raw_profiles, start=1):
                if not isinstance(p, dict):
                    continue
                profiles.append(p)
                normalized = normalize_profile_for_db(p)
                movie_id = normalized["movie_id"]
                print(f"[{idx}/{total}] Upserting movie_id={movie_id}")

                movie_exists = (
                    db.execute(select(Movie.id).where(Movie.id == movie_id).limit(1)).scalar_one_or_none()
                    is not None
                )
                if not movie_exists:
                    skipped_missing_movie += 1
                    continue

                row = db.scalars(
                    select(MovieVector).where(MovieVector.movie_id == movie_id).limit(1)
                ).first()

                if row is None:
                    row = MovieVector(
                        movie_id=movie_id,
                        emotion_scores=normalized["emotion_scores"],
                        narrative_traits=normalized["narrative_traits"],
                        ending_preference=normalized["ending_preference"],
                        embedding_vector=normalized["embedding_vector"],
                        direction_mood=normalized["direction_mood"],
                        character_relationship=normalized["character_relationship"],
                        embedding_text=normalized["embedding_text"],
                        updated_at=fixed_updated_at,
                    )
                    db.add(row)
                    inserted += 1
                else:
                    row.emotion_scores = normalized["emotion_scores"]
                    row.narrative_traits = normalized["narrative_traits"]
                    row.ending_preference = normalized["ending_preference"]
                    row.embedding_vector = normalized["embedding_vector"]
                    row.direction_mood = normalized["direction_mood"]
                    row.character_relationship = normalized["character_relationship"]
                    row.embedding_text = normalized["embedding_text"]
                    row.updated_at = fixed_updated_at
                    updated += 1

                if args.dry_run:
                    db.flush()
                else:
                    db.commit()
        else:
            movies = load_json(args.movies)
            if not isinstance(movies, list):
                raise ValueError("Movies input must be a JSON array.")

            taxonomy = emb.load_taxonomy(args.taxonomy)

            if args.movie_id is not None:
                movies = [m for m in movies if isinstance(m, dict) and m.get("id") == args.movie_id]

            if args.limit is not None:
                movies = movies[: args.limit]

            if not movies:
                print("No movies selected.")
                return

            bedrock_client = emb.get_bedrock_client()
            if bedrock_client is None and not args.allow_fallback:
                raise RuntimeError(
                    "Bedrock client init failed. Fill AWS credentials in .env or use --allow-fallback."
                )

            for idx, movie in enumerate(movies, start=1):
                if not isinstance(movie, dict):
                    continue
                print(
                    f"[{idx}/{len(movies)}] Processing movie_id={movie.get('id')} title={movie.get('title')}"
                )
                profile = build_profile_strict(movie, taxonomy, bedrock_client, args.allow_fallback)
                profiles.append(profile)
                normalized = normalize_profile_for_db(profile)
                movie_id = normalized["movie_id"]

                movie_exists = (
                    db.execute(select(Movie.id).where(Movie.id == movie_id).limit(1)).scalar_one_or_none()
                    is not None
                )
                if not movie_exists:
                    skipped_missing_movie += 1
                    continue

                row = db.scalars(
                    select(MovieVector).where(MovieVector.movie_id == movie_id).limit(1)
                ).first()
                if row is None:
                    row = MovieVector(
                        movie_id=movie_id,
                        emotion_scores=normalized["emotion_scores"],
                        narrative_traits=normalized["narrative_traits"],
                        ending_preference=normalized["ending_preference"],
                        embedding_vector=normalized["embedding_vector"],
                        direction_mood=normalized["direction_mood"],
                        character_relationship=normalized["character_relationship"],
                        embedding_text=normalized["embedding_text"],
                        updated_at=fixed_updated_at,
                    )
                    db.add(row)
                    inserted += 1
                else:
                    row.emotion_scores = normalized["emotion_scores"]
                    row.narrative_traits = normalized["narrative_traits"]
                    row.ending_preference = normalized["ending_preference"]
                    row.embedding_vector = normalized["embedding_vector"]
                    row.direction_mood = normalized["direction_mood"]
                    row.character_relationship = normalized["character_relationship"]
                    row.embedding_text = normalized["embedding_text"]
                    row.updated_at = fixed_updated_at
                    updated += 1

                if args.dry_run:
                    db.flush()
                else:
                    db.commit()

        if args.dry_run:
            db.rollback()
            print("Dry run complete. DB changes rolled back.")
        else:
            print("DB upsert complete.")

        output_path = Path(args.output)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
        print(f"Saved generated profiles to {output_path}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(
        {
            "processed_profiles": len(profiles),
            "inserted": inserted,
            "updated": updated,
            "skipped_missing_movie_fk": skipped_missing_movie,
            "updated_at": "2026-02-19T00:00:00+00:00",
            "dry_run": args.dry_run,
            "allow_fallback": args.allow_fallback,
        }
    )


if __name__ == "__main__":
    main()
