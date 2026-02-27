/**
 * LLM Chat API
 */
import { post, get } from './http';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  system_prompt?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface ChatResponse {
  response: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
}

export interface SystemPrompt {
  name: string;
  prompt: string;
}

/**
 * Send chat message to LLM
 */
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return post<ChatResponse>('/api/llm/chat', request);
}

/**
 * Get predefined system prompts
 */
export async function getSystemPrompts(): Promise<{ prompts: SystemPrompt[] }> {
  return get<{ prompts: SystemPrompt[] }>('/api/llm/system-prompts');
}
