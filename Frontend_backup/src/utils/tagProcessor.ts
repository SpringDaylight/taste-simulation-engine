/**
 * 태그 전처리 유틸리티
 * 이모티콘을 제거하고 '/' 구분자로 분리하여 개별 태그로 변환
 */

/**
 * 이모티콘과 공백을 제거하고 '/'로 분리된 태그들을 개별 태그로 변환
 * @param tags - 원본 태그 배열 (예: ["💕 로맨스 / 로코", "😂 코미디"])
 * @returns 전처리된 태그 배열 (예: ["로맨스", "로코", "코미디"])
 */
export function processGenreTags(tags: string[]): string[] {
  const processed: string[] = [];
  
  for (const tag of tags) {
    // 이모티콘 제거 (유니코드 이모티콘 범위)
    const withoutEmoji = tag.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '');
    
    // '/' 기준으로 분리
    const parts = withoutEmoji.split('/');
    
    for (const part of parts) {
      const trimmed = part.trim();
      if (trimmed && !processed.includes(trimmed)) {
        processed.push(trimmed);
      }
    }
  }
  
  return processed;
}
