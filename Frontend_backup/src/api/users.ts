/**
 * User API
 */
import { get } from './http';

export interface UserResponse {
  id: string;
  user_id: string;
  name: string;
  nickname: string;
  email: string;
  avatar_text?: string;
  created_at: string;
}

/**
 * Get current logged-in user info
 */
export async function getCurrentUser(): Promise<UserResponse> {
  return get<UserResponse>('/api/users/me');
}
