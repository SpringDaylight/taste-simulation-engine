from data.raw.tmdb_fetch import main as fetch_raw
from data.preprocess.clean_movie import main as preprocess_clean
from data.llm_enrich.build_movie_profile import main as enrich_llm
from data.embedding.build_embedding import main as build_embedding
from data.index.index_opensearch import main as index_opensearch


def main() -> None:
    fetch_raw()
    preprocess_clean()
    enrich_llm()
    build_embedding()
    index_opensearch()


if __name__ == "__main__":
    main()
