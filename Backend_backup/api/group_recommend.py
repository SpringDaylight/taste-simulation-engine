"""
그룹 영화 추천 API (커밋 559354d 기능 통합)
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import SessionLocal
from repositories.movie_vector import MovieVectorRepository
from ml.model_sample.analysis import group_recommendation, embedding
import os

router = APIRouter(prefix="/api/group", tags=["group-recommend"])


class GroupUser(BaseModel):
    user_id: str = Field(..., description="사용자 ID")
    name: str = Field(..., description="사용자 이름")
    text: str = Field(default="", description="사용자 취향 텍스트")
    likes: List[str] = Field(default_factory=list, description="선호 태그")
    dislikes: List[str] = Field(default_factory=list, description="비선호 태그")
    profile: Optional[Dict[str, Any]] = Field(default=None, description="사용자 프로필")


class GroupRecommendRequest(BaseModel):
    users: List[GroupUser] = Field(..., description="그룹 사용자 목록")
    top_k: int = Field(default=10, ge=1, le=50, description="추천할 영화 개수")
    candidate_k: int = Field(default=200, ge=10, le=500, description="후보 영화 개수")
    strategy: str = Field(default="mean", description="집계 전략: mean, min, median, trimmed_mean")
    genres: Optional[List[str]] = Field(default=None, description="장르 필터")
    year_from: Optional[int] = Field(default=None, description="개봉년도 시작")
    year_to: Optional[int] = Field(default=None, description="개봉년도 끝")
    use_bedrock: bool = Field(default=True, description="LLM 설명 생성 사용 여부")


class TagDetail(BaseModel):
    tag: str
    match_score: float
    user_score: Optional[float] = None
    movie_score: Optional[float] = None


class UserDetail(BaseModel):
    user_id: str
    name: str
    probability: float
    top_factors: List[str]
    emotion_tags: List[TagDetail]
    narrative_tags: List[TagDetail]
    ending_tags: List[TagDetail]
    dislike_penalty: float
    boost_score: float
    explanation: str


class RecommendedMovie(BaseModel):
    movie_id: int
    title: str
    genres: List[str]
    release_year: int
    group_score: float
    prefilter_score: float
    poster_url: Optional[str] = None
    per_user_detail: Optional[List[UserDetail]] = None


class GroupRecommendResponse(BaseModel):
    strategy: str
    topk: List[RecommendedMovie]
    candidates_count: int
    filters: Optional[Dict[str, Any]] = None


@router.post("/recommend-v2", response_model=GroupRecommendResponse)
async def recommend_group_v2(request: GroupRecommendRequest):
    """
    그룹 영화 추천 (커밋 559354d 기능 통합)
    
    - LLM 기반 사용자별 설명 생성
    - 벡터 DB 캐싱
    - 다양한 집계 전략 (mean, min, median, trimmed_mean)
    """
    import time
    start_time = time.time()
    print(f"\n{'='*80}")
    print(f"[그룹 추천 시작] 사용자 수: {len(request.users)}, 전략: {request.strategy}")
    print(f"{'='*80}")
    
    db = SessionLocal()
    try:
        # 1. Taxonomy 로드
        step_start = time.time()
        print(f"[1/8] Taxonomy 로드 중...")
        taxonomy_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "ml", "data", "emotion_tag.json"
        )
        if not os.path.exists(taxonomy_path):
            taxonomy_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "ml", "model_sample", "data", "emotion_tag.json"
            )
        if not os.path.exists(taxonomy_path):
            taxonomy_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data", "emotion_tag.json"
            )
        
        if os.path.exists(taxonomy_path):
            taxonomy = embedding.load_taxonomy(taxonomy_path)
            print(f"   Taxonomy 로드됨: {taxonomy_path}")
            print(f"   emotion tags: {len(taxonomy.get('emotion', {}).get('tags', []))}")
            print(f"   story_flow tags: {len(taxonomy.get('story_flow', {}).get('tags', []))}")
        else:
            # Fallback taxonomy (사용하지 않아야 함)
            print(f"   [WARN] Taxonomy 파일을 찾을 수 없어 fallback 사용")
            taxonomy = {
                "emotion": {"tags": ["감동", "따뜻", "긴장", "우울", "통쾌"]},
                "story_flow": {"tags": ["반전", "전개", "복선", "기승전결"]}
            }
        print(f"   완료 ({time.time() - step_start:.2f}초)")
        
        # 2. DB에서 영화 벡터 가져오기
        step_start = time.time()
        print(f"[2/8] 영화 벡터 로드 중...")
        repo = MovieVectorRepository(db)
        all_vectors = repo.get_all_with_movie_info()
        
        if not all_vectors:
            raise HTTPException(status_code=404, detail="영화 벡터 데이터가 없습니다")
        print(f"   완료: {len(all_vectors)}개 영화 ({time.time() - step_start:.2f}초)")
        
        # 3. 영화 데이터 변환
        step_start = time.time()
        print(f"[3/8] 영화 데이터 변환 중...")
        movies = []
        movie_profiles = []
        for vector_data in all_vectors:
            # release_year를 int로 변환 (datetime.date 객체일 수 있음)
            release_year = vector_data.get("release_year", 0)
            if hasattr(release_year, 'year'):  # datetime.date 객체인 경우
                release_year = release_year.year
            elif not isinstance(release_year, int):
                try:
                    release_year = int(release_year)
                except (ValueError, TypeError):
                    release_year = 0
            
            movie = {
                "id": vector_data["movie_id"],
                "title": vector_data["title"],
                "genres": vector_data.get("genres", []),
                "release_year": release_year,
                "runtime": 120,
                "poster_url": vector_data.get("poster_url"),
                "avg_rating": vector_data.get("avg_rating"),
                "synopsis": vector_data.get("synopsis")
            }
            movies.append(movie)
            
            profile = {
                "movie_id": vector_data["movie_id"],
                "id": vector_data["movie_id"],
                "title": vector_data["title"],
                "emotion_scores": vector_data["emotion_scores"],
                "narrative_traits": vector_data["narrative_traits"],
                "ending_preference": vector_data["ending_preference"]
            }
            movie_profiles.append(profile)
        print(f"   완료 ({time.time() - step_start:.2f}초)")
        
        # 4. 사용자 데이터 변환 및 DB에서 취향 로드
        step_start = time.time()
        print(f"[4/8] 사용자 데이터 변환 및 취향 로드 중...")
        from repositories.user_preference import UserPreferenceRepository
        pref_repo = UserPreferenceRepository(db)
        
        users = []
        for user in request.users:
            # 디버그: 요청에서 받은 데이터 확인
            print(f"     [DEBUG] {user.name} 요청 데이터:")
            print(f"       user_id: {user.user_id}")
            print(f"       profile type: {type(user.profile)}")
            print(f"       profile value: {user.profile}")
            print(f"       profile is None: {user.profile is None}")
            print(f"       not user.profile: {not user.profile}")
            
            user_dict = {
                "user_id": user.user_id,
                "name": user.name,
                "text": user.text,
                "likes": user.likes,
                "dislikes": user.dislikes,
                "profile": user.profile
            }
            
            # DB에서 사용자 취향 로드 (profile이 없는 경우 항상 시도)
            if not user.profile:
                print(f"     [DEBUG] {user.name}: DB 조회 시도 (user_id={user.user_id})...")
                
                # user_id로 먼저 users 테이블에서 실제 id를 찾기
                from repositories.user import UserRepository
                user_repo = UserRepository(db)
                db_user = user_repo.get_by_user_id(user.user_id)
                
                if not db_user:
                    # user_id로 못 찾으면 id로 직접 조회
                    db_user = user_repo.get(user.user_id)
                
                if db_user:
                    actual_user_id = db_user.id  # 실제 id 사용
                    print(f"     [DEBUG] users 테이블에서 찾음: id={actual_user_id}")
                    
                    db_pref = pref_repo.get_by_user_id(actual_user_id)
                    print(f"     [DEBUG] db_pref is None: {db_pref is None}")
                    
                    if db_pref and db_pref.preference_vector_json:
                        pref_json = db_pref.preference_vector_json
                        
                        # preference_vector_json에서 global 프로필 추출
                        if 'global' in pref_json:
                            # 신 형식: global 키가 있는 경우
                            user_profile = pref_json['global']
                        else:
                            # 구 형식: 최상위에 직접 있는 경우
                            user_profile = pref_json
                        
                        if isinstance(user_profile, dict):
                            # 중요: DB의 프로필을 그대로 사용 (이미 올바른 20-key 형식)
                            user_dict["profile"] = user_profile
                            print(f"     {user.name}: DB에서 취향 로드 완료")
                            print(f"       emotion keys: {len(user_profile.get('emotion_scores', {}))}, narrative keys: {len(user_profile.get('narrative_traits', {}))}")
                            # boost_tags와 penalty_tags도 DB에서 가져오기 (요청에 없는 경우)
                            if not user.likes and db_pref.boost_tags:
                                user_dict["likes"] = db_pref.boost_tags
                            if not user.dislikes and db_pref.penalty_tags:
                                user_dict["dislikes"] = db_pref.penalty_tags
                        else:
                            print(f"     {user.name}: DB 취향 형식 오류, text로 생성")
                    else:
                        print(f"     {user.name}: DB 취향 없음, text로 생성")
                else:
                    print(f"     {user.name}: users 테이블에서 찾을 수 없음, text로 생성")
            else:
                print(f"     {user.name}: 요청에서 제공된 프로필 사용 (건너뜀)")
            
            users.append(user_dict)
        print(f"   완료: {len(users)}명 ({time.time() - step_start:.2f}초)")
        
        # 5. 필터 설정
        step_start = time.time()
        print(f"[5/8] 벡터 DB 및 검색 준비 중...")
        filters = {}
        if request.genres:
            filters["genres"] = request.genres
        if request.year_from is not None:
            filters["year_from"] = request.year_from
        if request.year_to is not None:
            filters["year_to"] = request.year_to
        
        # 5-1. 그룹 멤버들이 본 영화 ID 수집 (모든 멤버가 본 영화 제외)
        from repositories.watched import WatchedMovieRepository
        watched_repo = WatchedMovieRepository(db)
        
        all_watched_movie_ids = set()
        for user in request.users:
            # user_id로 먼저 users 테이블에서 실제 id를 찾기
            from repositories.user import UserRepository
            user_repo = UserRepository(db)
            db_user = user_repo.get_by_user_id(user.user_id)
            
            if not db_user:
                db_user = user_repo.get(user.user_id)
            
            if db_user:
                watched_ids = watched_repo.get_watched_movie_ids(db_user.id)
                all_watched_movie_ids.update(watched_ids)
        
        if all_watched_movie_ids:
            print(f"   그룹 멤버들이 본 영화 {len(all_watched_movie_ids)}개 제외")
        
        # 6. 그룹 추천 실행
        print(f"   벡터 DB 로드 완료 ({time.time() - step_start:.2f}초)")
        step_start = time.time()
        print(f"[6/8] 그룹 프로필 생성 및 후보 검색 중...")
        from ml.model_sample.analysis.group_recommendation import (
            parse_users_from_profiles,
            load_or_build_db,
            average_profiles,
            apply_tag_nudges_to_group_profile,
            profile_to_vector,
            aggregate_group_score,
            build_user_profile,
            extract_factor_tag_details,
            build_movie_explanation_with_llm
        )
        from ml.model_sample.analysis.cal_sim import calculate_satisfaction_probability_improved
        
        # 사용자 프로필 생성
        user_profiles = [build_user_profile(u, taxonomy) for u in users]
        
        # 디버그: 사용자 프로필 확인 (콘솔 출력만)
        print(f"   [DEBUG] 사용자 프로필 생성 완료:")
        for i, (u, up) in enumerate(zip(users, user_profiles)):
            emotion_sum = sum(up.get('emotion_scores', {}).values())
            narrative_sum = sum(up.get('narrative_traits', {}).values())
            emotion_keys = list(up.get('emotion_scores', {}).keys())
            narrative_keys = list(up.get('narrative_traits', {}).keys())
            
            print(f"     사용자 {i+1} ({u['name']}):")
            print(f"       emotion_scores: {len(emotion_keys)}개 키, 합계={emotion_sum:.3f}")
            print(f"       narrative_traits: {len(narrative_keys)}개 키, 합계={narrative_sum:.3f}")
            print(f"       emotion 샘플 키: {emotion_keys[:3]}")
            print(f"       narrative 샘플 키: {narrative_keys[:3]}")
            
            if emotion_sum == 0 and narrative_sum == 0:
                print(f"       ⚠️ 경고: 프로필이 비어있습니다!")
        
        # Bedrock 클라이언트
        explainer_client = None
        if request.use_bedrock:
            explainer_client = embedding.get_bedrock_client()
        
        # 벡터 DB 로드/생성
        e_keys = taxonomy.get("emotion", {}).get("tags", [])
        n_keys = taxonomy.get("story_flow", {}).get("tags", [])
        
        db_cache_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "cache", "movie_vecdb.pkl"
        )
        os.makedirs(os.path.dirname(db_cache_path), exist_ok=True)
        
        from ml.model_sample.analysis.vector_db import LocalVectorDB, build_vector_db, profile_to_vector
        
        # DB 캐시 사용
        # 차원 불일치 방지: taxonomy 키 개수가 변경되면 캐시 무효화
        expected_dims = len(e_keys) + len(n_keys) + 3  # ending 3개
        cache_valid = False
        
        if os.path.exists(db_cache_path):
            try:
                vec_db = LocalVectorDB()
                vec_db.load(db_cache_path)
                # 캐시된 벡터 차원 확인
                if len(vec_db.vectors) > 0:
                    cached_dims = vec_db.vectors[0].shape[0]
                    if cached_dims == expected_dims:
                        cache_valid = True
                        print(f"   벡터 DB 캐시 로드 완료 ({cached_dims}차원)")
                    else:
                        print(f"   [WARN] 캐시 차원 불일치 (캐시: {cached_dims}, 예상: {expected_dims}) - 재생성")
            except Exception as e:
                print(f"   [WARN] 캐시 로드 실패: {e} - 재생성")
        
        if not cache_valid:
            print(f"   벡터 DB 생성 중... ({expected_dims}차원)")
            vec_db = build_vector_db(movies, movie_profiles, e_keys, n_keys)
            vec_db.save(db_cache_path)
            print(f"   벡터 DB 저장 완료")
        
        # 그룹 프로필 생성
        group_profile = average_profiles(user_profiles, e_keys, n_keys)
        
        # 그룹 boost/penalty 태그
        group_boost = []
        group_penalty = []
        for u in users:
            group_boost.extend(u.get("likes", []) or [])
            group_penalty.extend(u.get("dislikes", []) or [])
        
        group_profile = apply_tag_nudges_to_group_profile(
            group_profile,
            e_keys,
            n_keys,
            boost_tags=group_boost,
            penalty_tags=group_penalty,
            boost_nudge=0.08,
            penalty_nudge=0.08
        )
        
        query_vec = profile_to_vector(group_profile, e_keys, n_keys)
        
        # 후보 검색
        candidates = vec_db.search(query_vec, k=request.candidate_k, filters=filters if filters else None)
        
        # watched 영화 필터링
        if all_watched_movie_ids:
            original_count = len(candidates)
            candidates = [c for c in candidates if c["metadata"].get("id") not in all_watched_movie_ids]
            filtered_count = original_count - len(candidates)
            if filtered_count > 0:
                print(f"   후보에서 본 영화 {filtered_count}개 제외됨")
        
        print(f"   후보 검색 완료: {len(candidates)}개 ({time.time() - step_start:.2f}초)")
        
        # 랭킹 (1단계: 만족도 계산만, LLM 설명은 나중에)
        step_start = time.time()
        print(f"[7/8] 사용자별 만족도 계산 중... (후보 {len(candidates)}개)")
        
        # 첫 번째 영화로 디버그 (한 번만)
        if candidates:
            first_movie = candidates[0]
            first_meta = first_movie["metadata"]
            first_profile = first_meta.get("profile") or {}
            print(f"   [DEBUG] 첫 번째 영화 '{first_meta.get('title')}':")
            print(f"     movie emotion keys: {len(first_profile.get('emotion_scores', {}))}개")
            print(f"     movie narrative keys: {len(first_profile.get('narrative_traits', {}))}개")
            print(f"     movie emotion 샘플: {list(first_profile.get('emotion_scores', {}).keys())[:3]}")
            
            for u, up in zip(users, user_profiles):
                res = calculate_satisfaction_probability_improved(
                    user_profile=up,
                    movie_profile=first_profile,
                    dislikes=u.get("dislikes", []),
                    boost_tags=u.get("likes", []),
                    penalty_weight=0.7,
                    boost_weight=0.03,
                    use_sigmoid=True,
                    sigmoid_k=6.0,
                    sigmoid_x0=0.5
                )
                prob = float(res.get("probability", 0.0))
                breakdown = res.get("breakdown", {}) or {}
                print(f"     {u['name']}: {prob*100:.1f}% (base: {breakdown.get('emotion_similarity', 0):.3f}, "
                      f"{breakdown.get('narrative_similarity', 0):.3f}, {breakdown.get('ending_similarity', 0):.3f})")
        
        ranked = []
        for idx, item in enumerate(candidates):
            if idx % 50 == 0 and idx > 0:
                print(f"   진행: {idx}/{len(candidates)} 영화 처리 중...")
            
            meta = item["metadata"]
            movie_profile = meta.get("profile") or {}
            movie_title = meta.get("title", "")
            movie_id = meta.get("id")
            
            per_user_probs = []
            per_user_data = []  # LLM 설명 없이 기본 데이터만 저장
            
            for u, up in zip(users, user_profiles):
                res = calculate_satisfaction_probability_improved(
                    user_profile=up,
                    movie_profile=movie_profile,
                    dislikes=u.get("dislikes", []),
                    boost_tags=u.get("likes", []),
                    penalty_weight=0.7,
                    boost_weight=0.03,
                    use_sigmoid=True,
                    sigmoid_k=6.0,
                    sigmoid_x0=0.5
                )
                prob = float(res.get("probability", 0.0))
                per_user_probs.append(prob)
                
                breakdown = res.get("breakdown", {}) or {}
                top_factors = breakdown.get("top_factors", []) or []
                
                # LLM 설명 없이 기본 데이터만 저장
                per_user_data.append({
                    "user": u,
                    "user_profile": up,
                    "probability": prob,
                    "breakdown": breakdown,
                    "top_factors": top_factors
                })
            
            group_score = aggregate_group_score(per_user_probs, request.strategy)
            
            # release_year를 int로 변환
            release_year = meta.get("release_year")
            if hasattr(release_year, 'year'):  # datetime.date 객체인 경우
                release_year = release_year.year
            elif not isinstance(release_year, int):
                try:
                    release_year = int(release_year) if release_year else 0
                except (ValueError, TypeError):
                    release_year = 0
            
            ranked.append({
                "movie_id": movie_id,
                "title": movie_title,
                "genres": meta.get("genres", []),
                "release_year": release_year,
                "group_score": group_score,
                "prefilter_score": float(item.get("score", 0.0)),
                "poster_url": meta.get("poster_url"),
                "metadata": meta,
                "per_user_data": per_user_data  # 임시 데이터
            })
        
        # 정렬
        ranked.sort(key=lambda x: x["group_score"], reverse=True)
        topk = ranked[:request.top_k]
        print(f"   만족도 계산 완료 ({time.time() - step_start:.2f}초)")
        
        # Top-K에 대해서만 LLM 설명 생성
        if explainer_client:
            step_start = time.time()
            print(f"[7.5/8] Top-{len(topk)} 영화에 대한 LLM 설명 생성 중...")
            for movie_data in topk:
                per_user_detail = []
                for user_data in movie_data["per_user_data"]:
                    u = user_data["user"]
                    up = user_data["user_profile"]
                    prob = user_data["probability"]
                    breakdown = user_data["breakdown"]
                    top_factors = user_data["top_factors"]
                    
                    factor_tag_details = extract_factor_tag_details(
                        user_profile=up,
                        movie_profile=movie_data["metadata"].get("profile") or {},
                        top_factors=top_factors,
                        top_n=1
                    )
                    
                    explanation = build_movie_explanation_with_llm(
                        user=u,
                        movie_meta=movie_data["metadata"],
                        probability=prob,
                        breakdown=breakdown,
                        factor_tag_details=factor_tag_details,
                        bedrock_client=explainer_client
                    )
                    
                    per_user_detail.append({
                        "user_id": u["user_id"],
                        "name": u["name"],
                        "probability": prob,
                        "top_factors": top_factors,
                        "emotion_tags": factor_tag_details.get("emotion_tags", []),
                        "narrative_tags": factor_tag_details.get("narrative_tags", []),
                        "ending_tags": factor_tag_details.get("ending_tags", []),
                        "dislike_penalty": breakdown.get("dislike_penalty", 0.0),
                        "boost_score": breakdown.get("boost_score", 0.0),
                        "explanation": explanation
                    })
                
                movie_data["per_user_detail"] = per_user_detail
                del movie_data["per_user_data"]  # 임시 데이터 제거
                del movie_data["metadata"]  # metadata도 제거
            print(f"   LLM 설명 생성 완료 ({time.time() - step_start:.2f}초)")
        else:
            # LLM 없이 기본 설명만 생성
            for movie_data in topk:
                per_user_detail = []
                for user_data in movie_data["per_user_data"]:
                    u = user_data["user"]
                    up = user_data["user_profile"]
                    prob = user_data["probability"]
                    breakdown = user_data["breakdown"]
                    top_factors = user_data["top_factors"]
                    
                    factor_tag_details = extract_factor_tag_details(
                        user_profile=up,
                        movie_profile=movie_data["metadata"].get("profile") or {},
                        top_factors=top_factors,
                        top_n=1
                    )
                    
                    from ml.model_sample.analysis.group_recommendation import build_user_explanation
                    explanation = build_user_explanation(breakdown, factor_tag_details=factor_tag_details)
                    
                    per_user_detail.append({
                        "user_id": u["user_id"],
                        "name": u["name"],
                        "probability": prob,
                        "top_factors": top_factors,
                        "emotion_tags": factor_tag_details.get("emotion_tags", []),
                        "narrative_tags": factor_tag_details.get("narrative_tags", []),
                        "ending_tags": factor_tag_details.get("ending_tags", []),
                        "dislike_penalty": breakdown.get("dislike_penalty", 0.0),
                        "boost_score": breakdown.get("boost_score", 0.0),
                        "explanation": explanation
                    })
                
                movie_data["per_user_detail"] = per_user_detail
                del movie_data["per_user_data"]
                del movie_data["metadata"]
        
        # 최종 응답
        step_start = time.time()
        print(f"[8/8] 응답 생성 중...")
        response = GroupRecommendResponse(
            strategy=request.strategy,
            topk=[RecommendedMovie(**r) for r in topk],
            candidates_count=len(candidates),
            filters=filters if filters else None
        )
        print(f"   완료 ({time.time() - step_start:.2f}초)")
        
        total_time = time.time() - start_time
        print(f"\n{'='*80}")
        print(f"[그룹 추천 완료] 총 소요 시간: {total_time:.2f}초")
        print(f"  - 추천 영화: {len(topk)}개")
        print(f"  - 후보 영화: {len(candidates)}개")
        print(f"  - LLM 사용: {'예' if request.use_bedrock else '아니오'}")
        print(f"{'='*80}\n")
        
        return response
        
    except Exception as e:
        error_time = time.time() - start_time
        print(f"\n{'='*80}")
        print(f"[그룹 추천 실패] 오류 발생 ({error_time:.2f}초 경과)")
        print(f"  에러: {str(e)}")
        print(f"{'='*80}\n")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"그룹 추천 실패: {str(e)}")
    finally:
        db.close()
