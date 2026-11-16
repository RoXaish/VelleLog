import { vi } from 'vitest';

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function requestPath(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.pathname + input.search;
  return input.url;
}

export function requestMethod(init?: RequestInit): string {
  return (init?.method ?? 'GET').toUpperCase();
}

export function requestHeaders(init?: RequestInit): Headers {
  return new Headers(init?.headers);
}

export type FetchHandler = (
  input: RequestInfo | URL,
  init?: RequestInit
) => Response | Promise<Response>;

export function installFetchMock(handler: FetchHandler) {
  const mockedFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    return handler(input, init);
  });
  vi.stubGlobal('fetch', mockedFetch);
  return mockedFetch;
}
