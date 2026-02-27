import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import MainLayout from "../components/layout/MainLayout";

type SupportItem = {
  id: number;
  question: string;
  content: string[];
};

const noticeList: SupportItem[] = [
  {
    id: 101,
    question: "이용 가이드 업데이트 안내 (2/21)",
    content: [
      "리뷰 작성 흐름이 더 단순해졌어요.",
      "스포일러 표기 기준과 예시를 추가했어요.",
      "프로필 공개 범위 설정 방법을 보강했어요.",
    ],
  },
  {
    id: 102,
    question: "리뷰/평점 작성 정책 변경 안내",
    content: [
      "과도한 비방/혐오 표현은 숨김 처리될 수 있어요.",
      "같은 내용의 반복 리뷰는 노출이 제한될 수 있어요.",
      "수정/삭제는 작성 후 7일 이내에 자유롭게 가능해요.",
    ],
  },
  {
    id: 103,
    question: "추천/취향 분석 결과 해석 팁",
    content: [
      "상위 키워드는 최근 시청/평점 행동을 반영해요.",
      "피하고 싶은 장르는 설문에서 수정할 수 있어요.",
      "평점/찜/리뷰 활동이 많을수록 정확도가 올라가요.",
    ],
  },
  {
    id: 104,
    question: "활동/피드 공개 범위 설정 안내",
    content: [
      "전체 공개/팔로워 공개/비공개 중 선택할 수 있어요.",
      "변경 즉시 내 활동 카드에 적용돼요.",
      "비공개 시 내 리뷰는 검색/피드에 노출되지 않아요.",
    ],
  },
];

const inquiryList: SupportItem[] = [
  {
    id: 201,
    question: "로그인이 되지 않아요",
    content: [
      "이메일/비밀번호를 다시 확인해 주세요.",
      "비밀번호 찾기 후에도 실패한다면 에러 메시지를 첨부해 주세요.",
      "발생 시간, 사용 기기/브라우저 정보를 함께 알려주세요.",
    ],
  },
  {
    id: 202,
    question: "리뷰/평점 작성이 반영되지 않아요",
    content: [
      "작성 직후에는 반영까지 1~3분 지연될 수 있어요.",
      "문제가 지속되면 영화명/작성 시각을 알려주세요.",
      "스크린샷을 첨부하면 빠른 확인이 가능해요.",
    ],
  },
  {
    id: 203,
    question: "프로필 정보(닉네임/소개) 수정 문의",
    content: [
      "프로필 > 편집에서 변경할 수 있어요.",
      "닉네임 중복 시 저장이 실패할 수 있어요.",
      "변경이 안 될 경우 현재 닉네임과 변경 요청값을 알려주세요.",
    ],
  },
  {
    id: 204,
    question: "추천이 이상하게 나와요",
    content: [
      "취향 설문을 다시 진행하면 추천이 갱신돼요.",
      "최근 평가/찜 목록이 반영될 때 시간이 걸릴 수 있어요.",
      "원하는 장르/키워드를 함께 알려주면 조정에 도움이 돼요.",
    ],
  },
  {
    id: 205,
    question: "활동/피드 공개 범위를 변경하고 싶어요",
    content: [
      "활동 > 공개 범위에서 설정할 수 있어요.",
      "변경 후에도 캐시로 보일 수 있어 새로고침을 권장해요.",
      "원하는 공개 범위를 명확히 적어주면 확인이 빨라요.",
    ],
  },
];

const faqList: SupportItem[] = [
  {
    id: 301,
    question: "비밀번호를 잊어버렸어요",
    content: [
      "로그인 화면의 비밀번호 찾기를 이용해 주세요.",
      "가입 이메일로 재설정 링크가 전송돼요.",
      "메일이 오지 않으면 스팸함을 확인해 주세요.",
    ],
  },
  {
    id: 302,
    question: "취향 분석은 어떻게 진행하나요?",
    content: [
      "회원가입 또는 마이페이지에서 설문을 시작할 수 있어요.",
      "선호 장르/키워드 선택 후 결과 카드가 생성돼요.",
      "언제든 재설문으로 최신 취향을 반영할 수 있어요.",
    ],
  },
  {
    id: 303,
    question: "리뷰/평점은 수정하거나 삭제할 수 있나요?",
    content: [
      "내 리뷰 카드의 더보기 메뉴에서 수정/삭제가 가능해요.",
      "수정 시 기존 평점과 내용이 즉시 갱신돼요.",
      "삭제한 리뷰는 복구할 수 없어요.",
    ],
  },
  {
    id: 304,
    question: "스포일러 표기는 어떻게 하나요?",
    content: [
      "리뷰 작성 화면에서 스포일러 체크를 켜 주세요.",
      "스포일러 표시된 리뷰는 요약이 가려져 보여요.",
      "중요 반전/결말 언급 시 반드시 표기해 주세요.",
    ],
  },
  {
    id: 305,
    question: "팔로워에게 내 활동이 모두 공개되나요?",
    content: [
      "공개 범위 설정에 따라 공개 범위가 달라져요.",
      "비공개로 설정하면 팔로워도 볼 수 없어요.",
      "활동 카드별로 공개 설정이 적용돼요.",
    ],
  },
  {
    id: 306,
    question: "알림 설정을 끄고 싶어요",
    content: [
      "프로필 > 알림 설정에서 항목별로 끌 수 있어요.",
      "좋아요/댓글/팔로우 알림을 개별로 제어할 수 있어요.",
      "설정 후 바로 반영되지 않으면 앱을 재실행해 주세요.",
    ],
  },
];

export function SupportPage() {
  const { pathname } = useLocation();
  const [openId, setOpenId] = useState<number | null>(null);
  const isNotice = pathname === "/notice";
  const isInquiry = pathname === "/inquiry";
  const items = isNotice ? noticeList : isInquiry ? inquiryList : faqList;
  const navClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? "active" : undefined;
  const detailLabel = isNotice ? "공지 내용" : isInquiry ? "문의 가이드" : "답변";

  useEffect(() => {
    setOpenId(null);
  }, [pathname]);

  return (
    <MainLayout>
      <main className="container">
        <section className="section card support-card">
          <div className="section-header one-line support-header">
            <div className="support-tabs" role="tablist" aria-label="고객센터">
              <NavLink to="/notice" className={navClass} role="tab">
                공지사항
              </NavLink>
              <NavLink to="/inquiry" className={navClass} role="tab">
                문의하기
              </NavLink>
              <NavLink to="/faq" className={navClass} role="tab">
                FAQ
              </NavLink>
            </div>
          </div>

          <div className="support-faq-list">
            {items.map((item) => {
              const isOpen = openId === item.id;
              const detailId = `support-detail-${item.id}`;
              return (
                <div
                  key={item.id}
                  className={`support-faq-item ${isOpen ? "is-open" : ""}`}
                >
                  <button
                    type="button"
                    className="support-faq-question"
                    aria-expanded={isOpen}
                    aria-controls={detailId}
                    onClick={() => setOpenId(isOpen ? null : item.id)}
                  >
                    <span>{item.question}</span>
                    <span className="faq-plus">{isOpen ? "−" : "+"}</span>
                  </button>
                  {isOpen && (
                    <div
                      className="support-faq-answer"
                      id={detailId}
                      role="region"
                      aria-label={`${item.question} 상세`}
                    >
                      <p className="support-detail-title">{detailLabel}</p>
                      <ul>
                        {item.content.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      </main>
    </MainLayout>
  );
}

export default SupportPage;

