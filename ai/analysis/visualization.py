"""
사용자 프로필 워드클라우드 생성기

마이페이지에서 사용자가 좋아하는 영화의 태그를 워드클라우드로 시각화
"""

import argparse
import json
from typing import Dict, List
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib import font_manager, rc

# 한글 폰트 설정
def setup_korean_font():
    """한글 폰트 설정"""
    try:
        # Windows
        font_path = "C:/Windows/Fonts/malgun.ttf"
        font_name = font_manager.FontProperties(fname=font_path).get_name()
        rc('font', family=font_name)
    except:
        try:
            # macOS
            rc('font', family='AppleGothic')
        except:
            print("⚠️  한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
    
    plt.rcParams['axes.unicode_minus'] = False


def load_user_preference(user_id: str, preference_file: str = 'user_preferences.json') -> Dict:
    """사용자 선호도 로드"""
    with open(preference_file, 'r', encoding='utf-8') as f:
        preferences = json.load(f)
    
    if user_id not in preferences:
        raise ValueError(f"사용자 '{user_id}'를 찾을 수 없습니다.")
    
    return preferences[user_id]


def generate_tag_wordcloud(
    user_id: str,
    preference_file: str = 'user_preferences.json',
    output_file: str = None,
    tag_type: str = 'boost'  # 'boost', 'penalty', or 'both'
):
    """
    사용자 프로필 태그 워드클라우드 생성
    
    Args:
        user_id: 사용자 ID
        preference_file: 선호도 파일 경로
        output_file: 출력 이미지 파일명 (None이면 화면에 표시)
        tag_type: 워드클라우드에 표시할 태그 종류
            - 'boost': 좋아하는 태그만
            - 'penalty': 싫어하는 태그만
            - 'both': 두 가지 모두 (색상 구분)
    """
    setup_korean_font()
    
    # 사용자 선호도 로드
    preference = load_user_preference(user_id, preference_file)
    
    boost_tags = preference.get('boost_tags', [])
    penalty_tags = preference.get('penalty_tags', [])
    boost_freq = preference.get('boost_tag_frequency', {})
    penalty_freq = preference.get('penalty_tag_frequency', {})
    
    print(f"\n{'='*60}")
    print(f"🎬 {user_id} 사용자 프로필 워드클라우드 생성")
    print(f"{'='*60}")
    print(f"좋아하는 태그: {len(boost_tags)}개")
    print(f"싫어하는 태그: {len(penalty_tags)}개")
    print(f"태그 종류: {tag_type}\n")
    
    # WordCloud 라이브러리 임포트 시도
    try:
        from wordcloud import WordCloud
    except ImportError:
        print("⚠️ wordcloud 라이브러리가 설치되지 않았습니다.")
        print("다음 명령어로 설치하세요: pip install wordcloud")
        
        # 대신 간단한 막대그래프로 표시
        print("\n대신 막대 그래프로 표시합니다...\n")
        create_tag_bar_chart(boost_tags, penalty_tags, boost_freq, penalty_freq, tag_type, output_file)
        return
    
    # 워드클라우드 생성
    if tag_type == 'boost':
        # 좋아하는 태그만
        tag_freq = boost_freq if boost_freq else {tag: 1 for tag in boost_tags}
        
        wc = WordCloud(
            font_path='C:/Windows/Fonts/malgun.ttf',  # Windows 한글 폰트
            width=800,
            height=400,
            background_color='white',
            colormap='Blues',
            relative_scaling=0.5,
            min_font_size=10
        ).generate_from_frequencies(tag_freq)
        
        # 시각화
        plt.figure(figsize=(12, 6))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        plt.title(f'👍 {user_id}님이 좋아하는 영화 태그', fontsize=16, pad=20)
        
    elif tag_type == 'penalty':
        # 싫어하는 태그만
        tag_freq = penalty_freq if penalty_freq else {tag: 1 for tag in penalty_tags}
        
        wc = WordCloud(
            font_path='C:/Windows/Fonts/malgun.ttf',
            width=800,
            height=400,
            background_color='white',
            colormap='Reds',
            relative_scaling=0.5,
            min_font_size=10
        ).generate_from_frequencies(tag_freq)
        
        plt.figure(figsize=(12, 6))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        plt.title(f'👎 {user_id}님이 싫어하는 영화 태그', fontsize=16, pad=20)
        
    else:  # both
        # 두 가지 모두 표시 (서브플롯)
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        # 좋아하는 태그
        boost_freq_data = boost_freq if boost_freq else {tag: 1 for tag in boost_tags}
        wc_boost = WordCloud(
            font_path='C:/Windows/Fonts/malgun.ttf',
            width=600,
            height=400,
            background_color='white',
            colormap='Blues',
            relative_scaling=0.5,
            min_font_size=10
        ).generate_from_frequencies(boost_freq_data)
        
        axes[0].imshow(wc_boost, interpolation='bilinear')
        axes[0].axis('off')
        axes[0].set_title('👍 좋아하는 태그', fontsize=14, pad=10)
        
        # 싫어하는 태그
        penalty_freq_data = penalty_freq if penalty_freq else {tag: 1 for tag in penalty_tags}
        wc_penalty = WordCloud(
            font_path='C:/Windows/Fonts/malgun.ttf',
            width=600,
            height=400,
            background_color='white',
            colormap='Reds',
            relative_scaling=0.5,
            min_font_size=10
        ).generate_from_frequencies(penalty_freq_data)
        
        axes[1].imshow(wc_penalty, interpolation='bilinear')
        axes[1].axis('off')
        axes[1].set_title('👎 싫어하는 태그', fontsize=14, pad=10)
        
        plt.suptitle(f'{user_id}님의 영화 취향 프로필', fontsize=18, y=0.98)
    
    plt.tight_layout()
    
    # 저장 또는 표시
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"💾 워드클라우드 저장: {output_file}")
    else:
        plt.show()
    
    plt.close()


def create_tag_bar_chart(
    boost_tags: List[str],
    penalty_tags: List[str],
    boost_freq: Dict,
    penalty_freq: Dict,
    tag_type: str,
    output_file: str = None
):
    """
    워드클라우드 대신 막대 그래프로 표시 (wordcloud 미설치 시 대안)
    """
    if tag_type == 'boost':
        tags = boost_tags[:20]  # 상위 20개
        freqs = [boost_freq.get(tag, 1) for tag in tags]
        
        plt.figure(figsize=(12, 8))
        plt.barh(range(len(tags)), freqs, color='steelblue')
        plt.yticks(range(len(tags)), tags)
        plt.xlabel('빈도', fontsize=12)
        plt.title('👍 좋아하는 영화 태그 Top 20', fontsize=14, pad=15)
        plt.gca().invert_yaxis()
        
    elif tag_type == 'penalty':
        tags = penalty_tags[:20]
        freqs = [penalty_freq.get(tag, 1) for tag in tags]
        
        plt.figure(figsize=(12, 8))
        plt.barh(range(len(tags)), freqs, color='indianred')
        plt.yticks(range(len(tags)), tags)
        plt.xlabel('빈도', fontsize=12)
        plt.title('👎 싫어하는 영화 태그 Top 20', fontsize=14, pad=15)
        plt.gca().invert_yaxis()
        
    else:  # both
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        
        # 좋아하는 태그
        boost_top = boost_tags[:15]
        boost_freqs = [boost_freq.get(tag, 1) for tag in boost_top]
        axes[0].barh(range(len(boost_top)), boost_freqs, color='steelblue')
        axes[0].set_yticks(range(len(boost_top)))
        axes[0].set_yticklabels(boost_top)
        axes[0].set_xlabel('빈도', fontsize=11)
        axes[0].set_title('👍 좋아하는 태그 Top 15', fontsize=12)
        axes[0].invert_yaxis()
        
        # 싫어하는 태그
        penalty_top = penalty_tags[:15]
        penalty_freqs = [penalty_freq.get(tag, 1) for tag in penalty_top]
        axes[1].barh(range(len(penalty_top)), penalty_freqs, color='indianred')
        axes[1].set_yticks(range(len(penalty_top)))
        axes[1].set_yticklabels(penalty_top)
        axes[1].set_xlabel('빈도', fontsize=11)
        axes[1].set_title('👎 싫어하는 태그 Top 15', fontsize=12)
        axes[1].invert_yaxis()
        
        plt.suptitle('영화 취향 프로필', fontsize=16, y=0.98)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"💾 그래프 저장: {output_file}")
    else:
        plt.show()
    
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='사용자 프로필 워드클라우드 생성')
    parser.add_argument('--user-id', default='user_test', help='사용자 ID')
    parser.add_argument('--preference-file', default='user_preferences.json', help='선호도 파일')
    parser.add_argument('--output', default=None, help='출력 이미지 파일명 (예: profile_wordcloud.png)')
    parser.add_argument('--type', choices=['boost', 'penalty', 'both'], default='both',
                        help='표시할 태그 종류: boost (좋아하는), penalty (싫어하는), both (둘다)')
    
    args = parser.parse_args()
    
    # 워드클라우드 생성
    generate_tag_wordcloud(
        user_id=args.user_id,
        preference_file=args.preference_file,
        output_file=args.output,
        tag_type=args.type
    )


if __name__ == '__main__':
    main()
