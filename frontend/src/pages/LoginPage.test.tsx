import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import {
  installFetchMock,
  jsonResponse,
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

async function openLogin() {
  renderApp('/login');
  await screen.findByRole('heading', { name: 'Welcome back.' });
}

describe('LoginPage', () => {
  it('shows required email and password validation', async () => {
    const fetchMock = installFetchMock((input) => {
      if (requestPath(input).endsWith('/api/auth/me')) {
        return jsonResponse({ detail: 'Could not validate credentials' }, 401);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });
    await openLogin();
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: 'Log in' }));

    expect(screen.getByText('Enter your email address.')).toBeInTheDocument();
    expect(screen.getByText('Enter your password.')).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) =>
          requestPath(input).endsWith('/api/auth/login') &&
          requestMethod(init) === 'POST'
      )
    ).toBe(false);
  });

  it('rejects malformed email addresses', async () => {
    installFetchMock((input) => {
      if (requestPath(input).endsWith('/api/auth/me')) {
        return jsonResponse({ detail: 'Could not validate credentials' }, 401);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });
    await openLogin();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Email'), 'alex@');
    await user.type(screen.getByLabelText('Password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument();
  });

  it('displays generic API failures clearly', async () => {
    installFetchMock((input, init) => {
      const path = requestPath(input);
      if (path.endsWith('/api/auth/me')) {
        return jsonResponse({ detail: 'Could not validate credentials' }, 401);
      }
      if (
        path.endsWith('/api/auth/login') &&
        requestMethod(init) === 'POST'
      ) {
        return jsonResponse({ detail: 'Invalid email or password' }, 401);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });
    await openLogin();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Email'), EMAIL);
    await user.type(screen.getByLabelText('Password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Invalid email or password'
    );
  });

  it('shows a loading state while logging in, then reaches the protected page', async () => {
    let resolveLogin: ((response: Response) => void) | undefined;
    let authenticated = false;

    installFetchMock((input, init) => {
      const path = requestPath(input);
      if (path.endsWith('/api/auth/me')) {
        return authenticated
          ? jsonResponse(USER)
          : jsonResponse({ detail: 'Could not validate credentials' }, 401);
      }
      if (path.endsWith('/api/auth/login') && requestMethod(init) === 'POST') {
        return new Promise<Response>((resolve) => {
          resolveLogin = (response) => {
            authenticated = true;
            resolve(response);
          };
        });
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    await openLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Email'), EMAIL);
    await user.type(screen.getByLabelText('Password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    await waitFor(() => expect(resolveLogin).toBeDefined());
    expect(
      screen.getByRole('button', { name: 'Signing in…' })
    ).toBeDisabled();

    resolveLogin?.(
      jsonResponse({ access_token: 'fake.jwt.token', token_type: 'bearer' })
    );

    expect(
      await screen.findByRole('heading', { name: 'Your space.' })
    ).toBeInTheDocument();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
});
