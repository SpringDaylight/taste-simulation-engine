
import json
import os
from moviemong import MovieMong

def demo_review_mong():
    print("🚀 리뷰몽 서비스 기능 검증 데모\n")
    
    # 테스터 ID 설정
    TEST_USER = "demo_tester_001"
    DATA_FILE = "moviemong_demo_data.json"
    
    # 0. 초기화 (기존 데이터 삭제)
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    
    mong = MovieMong(TEST_USER, data_file=DATA_FILE)
    print(f"✅ 사용자 초기화: {TEST_USER}")
    
    # ==========================================
    # 1. 데일리 질문 및 DB 저장 확인
    # ==========================================
    print("\n[Scenario 1: 데일리 질문 & DB 저장]")
    
    # 질문 가져오기
    q_data = mong.get_daily_question()
    print(f"1-1. 오늘의 질문: {q_data['question']}")
    
    # 답변하기
    answer = "영화는 역시 팝콘 맛이지!"
    print(f"1-2. 답변 제출: '{answer}'")
    res = mong.answer_daily_question(answer)
    print(f"   👉 결과: {res['message']} (보상: EXP+{res['reward']['exp']}, 팝콘+{res['reward']['popcorn']})")
    
    # 데이터 파일 직접 확인 (DB 저장 검증)
    print("1-3. JSON 파일(DB) 저장 확인:")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
        user_record = saved_data[TEST_USER]
        print(f"   📂 저장된 데이터: Last Question Date = {user_record['last_question_date']}")
        print(f"   📂 저장된 재화: Popcorn = {user_record['popcorn']}")
        
        if user_record['last_question_date'] and user_record['popcorn'] > 0:
            print("   ✅ DB 저장 성공!")
        else:
            print("   ❌ DB 저장 실패")

    # ==========================================
    # 2. 룰렛 (밥주기) 확률 로직 확인
    # ==========================================
    print("\n[Scenario 2: 룰렛 밥주기 (확률 테스트)]")
    print("백엔드 확률 설정: 팝콘(50%), 핫도그(25%), 콤보(15%), 오징어(9%), 치킨(1%)")
    print("👉 10회 연속 시도:")
    
    results = []
    for i in range(1, 11):
        roulette_res = mong.play_roulette()
        print(f"   #{i}: {roulette_res['prize']} (각도: {roulette_res['target_angle']}°)")
        results.append(roulette_res['prize'])
        
    print(f"\n   📊 결과 분포: {results}")

    # ==========================================
    # 3. 오리지널(기본) 맛 테스트
    # ==========================================
    print("\n[Scenario 3: 짧은 리뷰 (오리지널 맛) 테스트]")
    short_review_text = "가족이랑 봄"
    print(f"3-1. 리뷰 작성: '{short_review_text}'")
    
    review_res = mong.add_review(short_review_text)
    print(f"   👉 결과: {review_res['analysis']['flavor_name']} ({review_res['analysis']['flavor']})")
    
    if review_res['analysis']['flavor'] == "Original":
        print("   ✅ 오리지널 맛 판정 성공!")
    else:
        print(f"   ⚠️ 다른 맛 판정: {review_res['analysis']['flavor']}")

    # ==========================================
    # 4. 최종 상태 확인
    # ==========================================
    print("\n[Scenario 3: 최종 상태 (Home Data)]")
    home = mong.get_home_data()
    print(json.dumps(home, indent=2, ensure_ascii=False))
    
    # 이미지 경로 확인
    img_path = home['character']['image_path']
    print(f"\n   🖼️ 캐릭터 이미지 경로: {img_path}")
    if "리뷰몽_" in img_path:
        print("   ✅ 커스텀 이미지 매핑 성공!")

if __name__ == "__main__":
    demo_review_mong()
