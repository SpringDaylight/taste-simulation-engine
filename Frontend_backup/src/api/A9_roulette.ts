/**
 * Roulette API
 */
import { get, post } from "./http";

export interface RouletteConfigItem {
  label: string;
  probability: string;
  popcorn_gain: number;
  exp_gain: number;
}

export interface RouletteConfigResponse {
  items: RouletteConfigItem[];
}

export interface RouletteStatusResponse {
  can_spin: boolean;
  next_available_at?: string | null;
}

export interface RouletteSpinResponse {
  item: string;
  popcorn_gain: number;
  exp_gain: number;
  total_popcorn: number;
  total_exp: number;
}

export interface MoviemongHomeResponse {
  user_id: string;
  character: {
    level: number;
    stage: string;
    exp: number;
    next_level_exp: number | string;
    flavor: string;
    flavor_name: string;
    image_path: string;
  };
  currency: {
    popcorn: number;
  };
  daily_status: {
    can_answer_question: boolean;
    today_question?: string | null;
  };
}

export interface FeedingResponse {
  success: boolean;
  prize: string;
  target_angle: number;
  message: string;
  reward: {
    exp: number;
    popcorn: number;
  };
}

export function getRouletteConfig(): Promise<RouletteConfigResponse> {
  return get<RouletteConfigResponse>("/api/roulette/config");
}

export function getRouletteStatus(): Promise<RouletteStatusResponse> {
  return get<RouletteStatusResponse>("/api/roulette/status");
}

export function spinRoulette(): Promise<RouletteSpinResponse> {
  return post<RouletteSpinResponse>("/api/roulette/spin");
}

export function getMoviemongHome(): Promise<MoviemongHomeResponse> {
  return get<MoviemongHomeResponse>("/api/home");
}

export function playFeeding(): Promise<FeedingResponse> {
  return post<FeedingResponse>("/api/feeding");
}
