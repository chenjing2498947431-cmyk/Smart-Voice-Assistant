/**
 * LLMServer 接口的轻封装 (历史对话相关)。
 * 对接 LLMServer 的:
 *   POST   /v1/context/create
 *   GET    /v1/conversations
 *   GET    /v1/conversations/{sid}
 *   DELETE /v1/conversations/{sid}
 */

import { LLM_SERVER_HOST } from '@/config';

export interface ConversationSummary {
  sid: string;
  title: string;
  created_at: number;
  updated_at: number;
  last_message: string | null;
}

export interface MessageRow {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  response_id: string;
  created_at: number;
}

export interface ConversationDetail {
  conversation: {
    sid: string;
    title: string;
    system_prompt: string;
    latest_response_id: string;
    created_at: number;
    updated_at: number;
  };
  messages: MessageRow[];
}

const base = LLM_SERVER_HOST.replace(/\/+$/, '');

async function ok<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`${res.status}: ${await res.text()}`);
  }
  return (await res.json()) as T;
}

export async function createContext(systemPrompt?: string): Promise<string> {
  const res = await fetch(`${base}/v1/context/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(systemPrompt ? { system_prompt: systemPrompt } : {}),
  });
  const data = await ok<{ context_id: string }>(res);
  return data.context_id;
}

export async function listConversations(limit = 100): Promise<ConversationSummary[]> {
  const res = await fetch(`${base}/v1/conversations?limit=${limit}`);
  const data = await ok<{ conversations: ConversationSummary[] }>(res);
  return data.conversations;
}

export async function getConversation(sid: string): Promise<ConversationDetail> {
  const res = await fetch(`${base}/v1/conversations/${encodeURIComponent(sid)}`);
  return ok<ConversationDetail>(res);
}

export async function deleteConversation(sid: string): Promise<void> {
  const res = await fetch(`${base}/v1/conversations/${encodeURIComponent(sid)}`, {
    method: 'DELETE',
  });
  await ok<{ ok: boolean }>(res);
}
