import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import {
  installFetchMock,
  jsonResponse,
  requestHeaders,
  requestMethod,
  requestPath,
} from '../test/api';
import { renderApp } from '../test/renderApp';

const EMAIL = 'alex@example.com';
const PASSWORD = 's3cure-passphrase';
const USER = {
  id: 1,
  email: EMAIL,
  created_at: '2026-11-15T14:31:07',
  updated_at: '2026-11-15T14:31:07',
};

describe('authentication flow', () => {
  it('redirects anonymous users away from protected routes', async () => {
    installFetchMock((input) => {
      if (requestPath(input).endsWith('/api/auth/me')) {
        return jsonResponse({ detail: 'Could not validate credentials' }, 401);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/account');

    expect(
      await screen.findByRole('heading', { name: 'Welcome back.' })
    ).toBeInTheDocument();
  });

  it('keeps the landing page public', async () => {
    installFetchMock((input) => {
      if (requestPath(input).endsWith('/api/auth/me')) {
        return jsonResponse({ detail: 'Could not validate credentials' }, 401);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/');

    const heading = await screen.findByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent(/people who matter/i);
    expect(
      screen.queryByRole('heading', { name: 'Welcome back.' })
    ).not.toBeInTheDocument();
  });

  it('renders the protected account page for an authenticated session', async () => {
    installFetchMock((input) => {
      if (requestPath(input).endsWith('/api/auth/me')) {
        return jsonResponse(USER);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/account');

    expect(
      await screen.findByRole('heading', { name: 'Your space.' })
    ).toBeInTheDocument();
    expect(screen.getByText(EMAIL)).toBeInTheDocument();
    expect(screen.queryByText(/password_hash/i)).not.toBeInTheDocument();
  });

  it('shows a session loading state before resolving protected routes', async () => {
    let resolveMe: ((response: Response) => void) | undefined;
    installFetchMock((input) => {
      if (requestPath(input).endsWith('/api/auth/me')) {
        return new Promise<Response>((resolve) => {
          resolveMe = resolve;
        });
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/account');

    expect(screen.getByText('Checking your session…')).toBeInTheDocument();
    await waitFor(() => expect(resolveMe).toBeDefined());
    resolveMe?.(
      jsonResponse({ detail: 'Could not validate credentials' }, 401)
    );

    expect(
      await screen.findByRole('heading', { name: 'Welcome back.' })
    ).toBeInTheDocument();
  });

  it('shows the authenticated state on the landing page', async () => {
    installFetchMock((input) => {
      if (requestPath(input).endsWith('/api/auth/me')) {
        return jsonResponse(USER);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/');

    expect(
      await screen.findByRole('link', { name: 'Your space' })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: 'Log in' })
    ).not.toBeInTheDocument();
  });

  it('never stores the JWT and sends CSRF proof on logout', async () => {
    document.cookie = 'velle_csrf_token=test-csrf-token; path=/';
    let authenticated = false;
    const fetchMock = installFetchMock((input, init) => {
      const path = requestPath(input);
      const method = requestMethod(init);

      if (path.endsWith('/api/auth/me')) {
        return authenticated
          ? jsonResponse(USER)
          : jsonResponse({ detail: 'Could not validate credentials' }, 401);
      }
      if (path.endsWith('/api/auth/login') && method === 'POST') {
        authenticated = true;
        return jsonResponse({
          access_token: 'fake.jwt.token',
          token_type: 'bearer',
        });
      }
      if (path.endsWith('/api/auth/logout') && method === 'POST') {
        return new Response(null, { status: 204 });
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/login');
    await screen.findByRole('heading', { name: 'Welcome back.' });
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Email'), EMAIL);
    await user.type(screen.getByLabelText('Password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    await screen.findByRole('heading', { name: 'Your space.' });
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(
      fetchMock.mock.calls.map(([, init]) =>
        requestHeaders(init).get('Authorization')
      )
    ).toEqual(fetchMock.mock.calls.map(() => null));

    await user.click(screen.getByRole('button', { name: 'Sign out' }));

    const landingHeading = await screen.findByRole('heading', {
      name: /people who matter/i,
    });
    expect(landingHeading).toBeInTheDocument();

    const logoutCall = fetchMock.mock.calls.find(
      ([input, init]) =>
        requestPath(input).endsWith('/api/auth/logout') &&
        requestMethod(init) === 'POST'
    );
    expect(logoutCall).toBeDefined();
    expect(requestHeaders(logoutCall?.[1]).get('X-CSRF-Token')).toBe(
      'test-csrf-token'
    );
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
});
