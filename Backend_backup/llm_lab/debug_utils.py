"""
LLM 디버깅 유틸리티
"""
import json
from typing import Dict, Any


def print_request_body(body: Dict[str, Any]) -> None:
    """
    Request body를 보기 좋게 출력
    
    Args:
        body: Request body 딕셔너리
    """
    print("\n" + "="*80)
    print("📤 REQUEST BODY")
    print("="*80)
    
    # JSON을 예쁘게 포맷팅
    formatted = json.dumps(body, indent=2, ensure_ascii=False)
    
    # \n을 실제 개행으로 변환
    formatted = formatted.replace('\\n', '\n')
    
    print(formatted)
    print("="*80 + "\n")


def print_response_body(body: Dict[str, Any]) -> None:
    """
    Response body를 보기 좋게 출력
    
    Args:
        body: Response body 딕셔너리
    """
    print("\n" + "="*80)
    print("📥 RESPONSE BODY")
    print("="*80)
    
    # 주요 정보만 추출
    response_text = ""
    usage_info = {}
    
    if "content" in body and len(body["content"]) > 0:
        response_text = body["content"][0].get("text", "")
    
    if "usage" in body:
        usage_info = body["usage"]
    
    # 응답 텍스트 출력
    print("\n📝 Response Text:")
    print("-" * 80)
    # \n을 실제 개행으로 변환
    print(response_text.replace('\\n', '\n'))
    print("-" * 80)
    
    # 토큰 사용량 출력
    if usage_info:
        print("\n📊 Token Usage:")
        print(f"  Input Tokens:  {usage_info.get('input_tokens', 0):,}")
        print(f"  Output Tokens: {usage_info.get('output_tokens', 0):,}")
        print(f"  Total Tokens:  {usage_info.get('input_tokens', 0) + usage_info.get('output_tokens', 0):,}")
    
    # 메타데이터 출력
    print("\n🔍 Metadata:")
    print(f"  Model: {body.get('model', 'N/A')}")
    print(f"  Stop Reason: {body.get('stop_reason', 'N/A')}")
    
    print("="*80 + "\n")


def print_compact_request(body: Dict[str, Any]) -> None:
    """
    Request body를 간단하게 출력 (한 줄 요약)
    
    Args:
        body: Request body 딕셔너리
    """
    messages = body.get("messages", [])
    message_count = len(messages)
    
    # 첫 메시지 미리보기
    preview = ""
    if messages:
        first_content = messages[0].get("content", "")
        preview = first_content[:50] + "..." if len(first_content) > 50 else first_content
    
    print(f"📤 REQUEST: {message_count} message(s) | Preview: {preview}")


def print_compact_response(body: Dict[str, Any]) -> None:
    """
    Response body를 간단하게 출력 (한 줄 요약)
    
    Args:
        body: Response body 딕셔너리
    """
    response_text = ""
    if "content" in body and len(body["content"]) > 0:
        response_text = body["content"][0].get("text", "")
    
    preview = response_text[:50] + "..." if len(response_text) > 50 else response_text
    
    usage = body.get("usage", {})
    tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    
    print(f"📥 RESPONSE: {tokens:,} tokens | Preview: {preview}")


def print_debug_separator(title: str = "") -> None:
    """
    디버그 구분선 출력
    
    Args:
        title: 구분선 제목
    """
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'='*80}\n")


def print_candidate_retrieval(
    source: str,
    candidates: list,
    top_n: int = 5,
    show_details: bool = True
) -> None:
    """
    후보군 검색 결과를 보기 좋게 출력
    
    Args:
        source: 검색 소스 (keyword, vector, external 등)
        candidates: 후보 영화 리스트
        top_n: 상위 몇 개를 표시할지
        show_details: 상세 정보 표시 여부
    """
    source_icons = {
        "keyword": "🔍",
        "vector": "🎭",
        "external": "🌐",
        "hybrid": "🔀",
        "final": "🎬"
    }
    
    icon = source_icons.get(source, "📋")
    
    print(f"\n{icon} {source.upper()} 검색 결과: {len(candidates)}개 후보")
    print("-" * 80)
    
    if not candidates:
        print("  (후보 없음)")
        return
    
    # 상위 N개만 표시
    display_candidates = candidates[:top_n]
    
    for i, movie in enumerate(display_candidates, 1):
        title = movie.get('title', 'N/A')
        movie_id = movie.get('movie_id', 'N/A')
        
        print(f"  {i}. [{movie_id}] {title}")
        
        if show_details:
            # 최종 점수 정보 (final 소스인 경우)
            if source == "final" and 'final_score' in movie:
                final_score = movie.get('final_score', 0)
                weighted_score = movie.get('weighted_score', 0)
                multi_bonus = movie.get('multi_source_bonus', 0)
                
                # 소스별 원본 점수
                sources = movie.get('sources', [])
                keyword_score = movie.get('keyword_score', 0) if 'keyword' in sources else None
                emotion_score = movie.get('similarity_score', 0) if 'vector' in sources else None
                
                # 점수 설명
                print(f"     🎯 최종 점수: {final_score:.3f} ({final_score*100:.1f}%)")
                print(f"        = 가중치 적용 점수: {weighted_score:.3f}")
                
                if keyword_score is not None and emotion_score is not None:
                    print(f"          (키워드 {keyword_score:.3f} + 감성 {emotion_score:.3f})")
                elif keyword_score is not None:
                    print(f"          (키워드만: {keyword_score:.3f})")
                elif emotion_score is not None:
                    print(f"          (감성만: {emotion_score:.3f})")
                
                if multi_bonus > 0:
                    print(f"        + 다중 소스 보너스: {multi_bonus:.3f}")
            
            # 키워드 검색 결과
            elif source == "keyword":
                keyword_score = movie.get('keyword_score', 0)
                print(f"     키워드 매칭: {keyword_score:.3f} ({keyword_score*100:.1f}%)")
                print(f"        (제목 매칭 = 2점, 시놉시스 매칭 = 1점)")
            
            # 벡터 검색 결과
            elif source == "vector":
                emotion_score = movie.get('similarity_score', 0)
                print(f"     감성 유사도: {emotion_score:.3f} ({emotion_score*100:.1f}%)")
                print(f"        (코사인 유사도: -1.0 ~ 1.0)")
            
            # 하이브리드 점수 정보 (레거시)
            elif 'keyword_score' in movie and 'emotion_similarity' in movie:
                keyword_score = movie.get('keyword_score', 0)
                emotion_score = movie.get('emotion_similarity', 0)
                hybrid_score = movie.get('similarity_score', 0)
                print(f"     하이브리드: {hybrid_score:.3f} | 키워드={keyword_score:.3f} | 감성={emotion_score:.3f}")
            
            else:
                score = movie.get('similarity_score', 0)
                print(f"     점수: {score:.3f}")
            
            # 장르 정보
            genres = movie.get('genres', [])
            if genres:
                print(f"     장르: {', '.join(genres[:3])}")
            
            # 소스 정보 (다중 소스에서 발견된 경우)
            sources = movie.get('sources', [])
            if sources:
                print(f"     발견: {', '.join(sources)}")
    
    if len(candidates) > top_n:
        print(f"  ... 외 {len(candidates) - top_n}개")
    
    print("-" * 80)


def print_weight_decision(
    keyword_weight: float,
    emotion_weight: float,
    reason: str = ""
) -> None:
    """
    가중치 결정 정보를 보기 좋게 출력
    
    Args:
        keyword_weight: 키워드 가중치
        emotion_weight: 감성 가중치
        reason: 결정 이유
    """
    print(f"\n⚖️  가중치 결정")
    print("-" * 80)
    print(f"  키워드: {keyword_weight*100:>5.1f}% {'█' * int(keyword_weight * 20)}")
    print(f"  감성:   {emotion_weight*100:>5.1f}% {'█' * int(emotion_weight * 20)}")
    
    if reason:
        print(f"  이유: {reason}")
    
    print("-" * 80)


def print_candidate_merge(
    total_candidates: int,
    unique_candidates: int,
    multi_source_count: int
) -> None:
    """
    후보군 병합 정보를 출력
    
    Args:
        total_candidates: 전체 후보 수
        unique_candidates: 중복 제거 후 후보 수
        multi_source_count: 다중 소스에서 발견된 후보 수
    """
    print(f"\n🔗 후보군 병합")
    print("-" * 80)
    print(f"  전체 후보: {total_candidates}개")
    print(f"  고유 후보: {unique_candidates}개")
    print(f"  다중 소스 발견: {multi_source_count}개")
    print("-" * 80)
