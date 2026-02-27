/**
 * Authentication API
 */
import { post } from './http';

/*
export interface KakaoLoginResponse {
  auth_url: string;
}

export interface KakaoCallbackResponse {
  id?: string;
  user_id?: string | null;
  name: string;
  nickname?: string | null;
  email?: string | null;
  avatar_text: string;
  access_token: string;
  is_new_user: boolean;
  kakao_id?: string;
  provider?: string;
}

export interface KakaoSignupCompleteRequest {
  kakao_id: string;
  provider: string;
  nickname: string;
  email?: string;
  birth_date?: string;
  gender?: string;
}
*/

export interface SignupRequest {
  user_id: string;
  name: string;
  nickname: string;
  email: string;
  password: string;
  password_confirm: string;
  birth_date?: string;
}

export interface LoginRequest {
  user_id: string;
  password: string;
}

export interface PasswordChangeRequest {
  user_id: string;
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}

export interface AuthUserResponse {
  id: string;
  user_id: string;
  name: string;
  nickname: string;
  email: string;
  avatar_text?: string;
  created_at: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUserResponse;
}

/*
 * Kakao OAuth (unused)
 *
export function getKakaoLoginUrl(): Promise<KakaoLoginResponse> {
  return get<KakaoLoginResponse>('/api/auth/kakao/login');
}

export function handleKakaoCallback(code: string): Promise<KakaoCallbackResponse> {
  return get<KakaoCallbackResponse>('/api/auth/kakao/callback', { code });
}

export function completeKakaoSignup(data: KakaoSignupCompleteRequest): Promise<AuthUserResponse> {
  return post<AuthUserResponse>('/api/auth/kakao/complete-signup', data);
}
*/

/**
 * Local signup
 */
export function signup(data: SignupRequest): Promise<AuthUserResponse> {
  return post<AuthUserResponse>('/api/auth/signup', data);
}

/**
 * Local login
 */
export function login(data: LoginRequest): Promise<AuthTokenResponse> {
  return post<AuthTokenResponse>('/api/auth/login', data);
}

/**
 * Logout
 */
export function logout(): Promise<{ message: string }> {
  return post<{ message: string }>('/api/auth/logout');
}

/**
 * Change password for local user
 */
export function changePassword(
  data: PasswordChangeRequest
): Promise<{ message: string }> {
  return post<{ message: string }>('/api/auth/password', data);
}
