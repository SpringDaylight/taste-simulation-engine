"""
리뷰몽 (Review Mong) - 영화 취향 펫 키우기 서비스
사용자의 영화 기록 활동을 펫 육성 게임으로 변환하여 동기 부여를 제공하는 모듈 (Refactored)
"""

import json
import os
import sys

# 상위 폴더(ai) 및 루트 폴더를 path에 추가하여 import 문제 해결
current_dir = os.path.dirname(os.path.abspath(__file__))
ai_package_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(ai_package_dir)
sys.path.append(root_dir)

try:
    from ai.gamification import MovieMong, FLAVORS
except ImportError:
    # 패키지 내부에서 실행될 경우
    from ..gamification import MovieMong, FLAVORS

def main():
    print("🎬 리뷰몽(Review Mong) 시뮬레이션 시작 (Modularized)")
    
    # [Fix] Bedrock 연결을 위한 환경 변수 재설정 (AKIA 키 사용 시 세션 토큰 제거)
    from dotenv import load_dotenv
    load_dotenv(override=True)
    if os.getenv('AWS_ACCESS_KEY_ID', '').startswith('AKIA') and 'AWS_SESSION_TOKEN' in os.environ:
        del os.environ['AWS_SESSION_TOKEN']

    user_id = input("사용자 ID를 입력하세요 (기본: user_test): ").strip() or "user_test"
    
    mong = MovieMong(user_id)
    
    while True:
        print("\n[메뉴 선택]")
        print("1. ❓ 오늘의 질문 받기")
        print("2. 📝 리뷰 작성 (테스트)")
        print("3. ℹ️ 내 펫 상태 확인 (Home Data)")
        print("4. 🎰 밥주기 (룰렛)")
        print("5. 🚪 종료")
        
        choice = input("선택 > ")
        
        if choice == "1":
            q_data = mong.get_daily_question()
            print(f"\nQ. {q_data['question']}")
            
            if q_data['can_answer']:
                ans = input("답변 > ")
                res = mong.answer_daily_question(ans)
                print(f"✅ {res['message']} (보상: EXP +{res['reward']['exp']}, 팝콘 +{res['reward']['popcorn']})")
            else:
                print(f"🚫 {q_data['message']}")
            
        elif choice == "2":
            print("\n(테스트용) 영화 리뷰를 작성해주세요.")
            content = input("내용 > ")
            if not content:
                continue
            is_detail = len(content) >= 50
            if is_detail:
                print("(상세 리뷰로 인식됩니다)")
            else:
                print("(간편 리뷰로 인식됩니다)")
            mong.add_review(content, is_detail)
            
        elif choice == "3":
            data = mong.get_home_data()
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
        elif choice == "4":
            print("\n🎰 두근두근 룰렛을 돌립니다... (비용: 무료)")
            # 룰렛 돌리기
            result = mong.play_roulette()
            print(f"🎯 결과: {result['prize']} ({result.get('target_angle', 0)}도)")
            print(f"💬 {result['message']}")
            
            if 'reward' in result:
                r = result['reward']
                print(f"🎁 보상: EXP +{r['exp']}, 팝콘 +{r['popcorn']}")
            
        elif choice == "5":
            print("종료합니다.")
            break
        else:
            print("잘못된 입력입니다.")

if __name__ == "__main__":
    main()
