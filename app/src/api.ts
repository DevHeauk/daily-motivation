import { API_URL } from './config';
import { DailyQuote, Quote, ViewSource } from './types';

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(`${path} 요청 실패 (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export async function fetchTopics(): Promise<string[]> {
  const data = await fetchJSON<{ topics: string[] }>('/topics');
  return data.topics;
}

export function fetchTodayQuote(topic: string): Promise<DailyQuote> {
  return fetchJSON<DailyQuote>(`/quotes/today?topic=${encodeURIComponent(topic)}`);
}

// 이 기기가 본 적 없는 같은 주제의 명언. seen은 미리 받아 두고 아직 보여주지 않은 명언
export function fetchNextQuote(topic: string, deviceId: string, seen: string[]): Promise<Quote> {
  return fetchJSON<Quote>('/quotes/next', {
    method: 'POST',
    body: JSON.stringify({ topic, device_id: deviceId, seen }),
  });
}

export function recordView(
  deviceId: string,
  quoteId: string,
  source: ViewSource,
): Promise<{ ok: boolean }> {
  return fetchJSON('/views', {
    method: 'POST',
    body: JSON.stringify({ device_id: deviceId, quote_id: quoteId, source }),
  });
}

// token은 푸시 권한을 받았을 때만 보낸다. 없으면 서버의 기존 토큰이 유지된다
export function registerDevice(
  deviceId: string,
  topic: string,
  token?: string | null,
): Promise<{ ok: boolean }> {
  return fetchJSON('/devices', {
    method: 'POST',
    body: JSON.stringify({ device_id: deviceId, topic, token }),
  });
}
