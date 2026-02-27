import { get } from "./http";

export interface GroupUserSearchItem {
  id: string;
  user_id: string | null;
  name?: string | null;
  nickname: string | null;
  avatar_text?: string | null;
}

export interface GroupUserSearchResponse {
  users: GroupUserSearchItem[];
}

export function searchGroupUsers(
  query: string,
  limit = 20
): Promise<GroupUserSearchItem[]> {
  const trimmed = query.trim();
  if (!trimmed) return Promise.resolve([]);

  return get<GroupUserSearchResponse | GroupUserSearchItem[]>("/api/users/search", {
    query: trimmed,
    limit,
  }).then((response) => (Array.isArray(response) ? response : response.users));
}
