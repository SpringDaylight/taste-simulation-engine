/**
 * 리뷰 키워드 태그 선택 컴포넌트
 * 4개 그룹에서 각 최소 1개 필수 선택, 다중선택 가능
 */
import "./ReviewKeywordSelector.css";

interface KeywordItem {
    emoji: string;
    label: string;
    value: string;
}

interface KeywordGroup {
    id: string;
    title: string;
    items: KeywordItem[];
}

export const KEYWORD_GROUPS: KeywordGroup[] = [
    {
        id: "emotion",
        title: "Q1. 감상 후 느낌",
        items: [
            { emoji: "😭", label: "휴지 필수, 눈물 콧물 다 뺐어요", value: "sad" },
            { emoji: "🤣", label: "배꼽 빠지게 웃겨요", value: "funny" },
            { emoji: "🧸", label: "마음이 몽글몽글해지는 힐링 영화예요", value: "healing" },
            { emoji: "😱", label: "긴장감 대박, 손에 땀을 쥐어요", value: "tense" },
            { emoji: "🍠", label: "고구마 먹은 듯 답답하고 화나요", value: "frustrating" },
            { emoji: "🥱", label: "너무 지루해서 졸 뻔했어요", value: "boring" },
            { emoji: "😖", label: "보고 나서 기분이 찝찝하고 불쾌해요", value: "unpleasant" },
            { emoji: "💭", label: "여운이 길게 남아서 생각이 많아져요", value: "lingering" },
            { emoji: "🤩", label: "가슴이 벅차오르고 희망적이에요", value: "inspiring" },
            { emoji: "👻", label: "무서워서 잠 못 잘 것 같아요", value: "scary" },
        ],
    },
    {
        id: "narrative",
        title: "Q2. 스토리와 전개",
        items: [
            { emoji: "⚡", label: "반전이 소름 돋아요", value: "plot_twist" },
            { emoji: "🏎️", label: "전개가 시원시원하고 빨라요", value: "fast_paced" },
            { emoji: "🧱", label: "스토리가 탄탄하고 개연성 있어요", value: "solid_story" },
            { emoji: "🎓", label: "교훈과 메시지가 묵직해요", value: "message" },
            { emoji: "🤷", label: "스토리가 뻔하고 예상이 가요", value: "cliche" },
            { emoji: "📉", label: "결말이 허무하고 이해가 안 돼요", value: "bad_ending" },
            { emoji: "🐢", label: "전개가 느리고 질질 끌어요", value: "slow_paced" },
            { emoji: "☔", label: "억지로 울리려고 해서 거부감 들어요", value: "forced_tears" },
            { emoji: "🗝️", label: "결말이 열려 있어서 해석이 필요해요", value: "open_ending" },
            { emoji: "🗣️", label: "대사가 명대사 잔치예요", value: "great_lines" },
        ],
    },
    {
        id: "production",
        title: "Q3. 연출 및 퀄리티",
        items: [
            { emoji: "✨", label: "영상미가 화려하고 색감이 예뻐요", value: "visual_stunning" },
            { emoji: "🎧", label: "OST가 좋아서 플레이리스트에 넣었어요", value: "great_ost" },
            { emoji: "🎭", label: "배우들의 연기력이 미쳤어요", value: "acting_god" },
            { emoji: "🤖", label: "연기가 어색해서 몰입이 깨져요", value: "acting_awkward" },
            { emoji: "💥", label: "액션 장면이 타격감 넘치고 시원해요", value: "great_action" },
            { emoji: "🎬", label: "감독의 연출력이 돋보여요", value: "great_directing" },
            { emoji: "👗", label: "의상이나 배경 세트가 멋져요", value: "art_costume" },
            { emoji: "👾", label: "CG 티가 많이 나고 어색해요", value: "bad_cg" },
            { emoji: "🔊", label: "음향 효과가 리얼해서 현장감 있어요", value: "good_sound" },
            { emoji: "✂️", label: "편집이 산만해서 집중하기 힘들어요", value: "messy_editing" },
        ],
    },
    {
        id: "vibe",
        title: "Q4. 관람 가이드 & 분위기",
        items: [
            { emoji: "🍿", label: "아무 생각 없이 즐기는 킬링타임용이에요", value: "killing_time" },
            { emoji: "🩸", label: "잔인하거나 피가 많이 나와요", value: "violent" },
            { emoji: "💖", label: "썸 타는 사람이나 연인과 보기 딱이에요", value: "date_movie" },
            { emoji: "👨‍👩‍👧‍👦", label: "가족과 다 같이 봐도 민망하지 않아요", value: "family_safe" },
            { emoji: "🏠", label: "혼자 조용히 집중해서 보는 게 좋아요", value: "solo_watch" },
            { emoji: "👽", label: "취향을 많이 타는 매니아 영화예요", value: "cult_classic" },
            { emoji: "🔞", label: "선정적인 장면이 포함되어 있어요", value: "sexual" },
            { emoji: "🤢", label: "밥 먹으면서 보기엔 비위 상해요", value: "gore_warning" },
            { emoji: "🔄", label: "n차 관람하고 싶을 정도로 매력 있어요", value: "rewatch_value" },
            { emoji: "🧠", label: "내용은 어렵지만 지적 호기심을 자극해요", value: "intellectual" },
        ],
    },
];

export const getKeywordLabel = (value: string): string => {
    for (const group of KEYWORD_GROUPS) {
        const found = group.items.find(item => item.value === value);
        if (found) return found.label;
    }
    return value;
};

interface ReviewKeywordSelectorProps {
    selected: string[];
    onChange: (next: string[]) => void;
    /** 제출 시도 후 미선택 그룹 표시용 */
    showErrors?: boolean;
}

export default function ReviewKeywordSelector({
    selected,
    onChange,
    showErrors = false,
}: ReviewKeywordSelectorProps) {
    const toggle = (value: string) => {
        if (selected.includes(value)) {
            onChange(selected.filter((v) => v !== value));
        } else {
            onChange([...selected, value]);
        }
    };

    const isGroupEmpty = (group: KeywordGroup) =>
        !group.items.some((item) => selected.includes(item.value));

    return (
        <div className="review-keyword-selector">
            {KEYWORD_GROUPS.map((group) => {
                const empty = isGroupEmpty(group);
                const hasError = showErrors && empty;
                return (
                    <div
                        key={group.id}
                        className={`keyword-group${hasError ? " keyword-group--error" : ""}`}
                    >
                        <div className="keyword-group-header">
                            <span className="keyword-group-title">{group.title}</span>
                            <span className="keyword-group-required">
                                {hasError ? "⚠ 1개 이상 선택해주세요" : "필수 1개 이상"}
                            </span>
                        </div>
                        <div className="keyword-chips">
                            {group.items.map((item) => {
                                const active = selected.includes(item.value);
                                return (
                                    <button
                                        key={item.value}
                                        type="button"
                                        className={`keyword-chip${active ? " keyword-chip--active" : ""}`}
                                        onClick={() => toggle(item.value)}
                                        aria-pressed={active}
                                    >
                                        <span className="keyword-chip-emoji">{item.emoji}</span>
                                        <span className="keyword-chip-label">{item.label}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
