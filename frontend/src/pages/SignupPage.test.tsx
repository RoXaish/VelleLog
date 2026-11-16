import { screen } from '@testing-library/react';
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

function mockAnonymousMe(extra?: Parameters<typeof installFetchMock>[0]) {
  return installFetchMock((input, init) => {
    const path = requestPath(input);
    if (path.endsWith('/api/auth/me')) {
      return jsonResponse({ detail: 'Could not validate credentials' }, 401);
    }
    if (extra) {
      const response = extra(input, init);
      if (response) return response;
    }
    return jsonResponse({ detail: 'Not found' }, 404);
  });
}

async function openSignup() {
  renderApp('/signup');
  await screen.findByRole('heading', { name: 'Create your account.' });
}

describe('SignupPage', () => {
  it('shows required field validation before submitting', async () => {
    const fetchMock = mockAnonymousMe();
    await openSignup();
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(screen.getByText('Enter your email address.')).toBeInTheDocument();
    expect(screen.getByText('Create a password.')).toBeInTheDocument();
    expect(screen.getByText('Confirm your password.')).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) =>
          requestPath(input).endsWith('/api/auth/register') &&
          requestMethod(init) === 'POST'
      )
    ).toBe(false);
  });

  it('validates email format and password length', async () => {
    mockAnonymousMe();
    await openSignup();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Email'), 'not-an-email');
    await user.type(screen.getByLabelText('Password', { exact: true }), 'short');
    await user.type(screen.getByLabelText('Confirm password'), 'short');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument();
    expect(screen.getByText('Use at least 8 characters.')).toBeInTheDocument();
  });

  it('rejects mismatched passwords without calling the API', async () => {
    const fetchMock = mockAnonymousMe();
    await openSignup();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Email'), EMAIL);
    await user.type(screen.getByLabelText('Password', { exact: true }), PASSWORD);
    await user.type(screen.getByLabelText('Confirm password'), 'different-pass');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) =>
          requestPath(input).endsWith('/api/auth/register') &&
          requestMethod(init) === 'POST'
      )
    ).toBe(false);
  });

  it('displays API errors from the backend', async () => {
    mockAnonymousMe((input, init) => {
      if (
        requestPath(input).endsWith('/api/auth/register') &&
        requestMethod(init) === 'POST'
      ) {
        return jsonResponse({ detail: 'Email already registered' }, 409);
      }
      return undefined as unknown as Response;
    });
    await openSignup();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Email'), EMAIL);
    await user.type(screen.getByLabelText('Password', { exact: true }), PASSWORD);
    await user.type(screen.getByLabelText('Confirm password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Email already registered'
    );
    expect(
      screen.getByRole('button', { name: 'Create account' })
    ).toBeEnabled();
  });

  it('toggles password visibility accessibly', async () => {
    mockAnonymousMe();
    await openSignup();
    const user = userEvent.setup();
    const password = screen.getByLabelText('Password', { exact: true });

    expect(password).toHaveAttribute('type', 'password');
    await user.click(screen.getByRole('button', { name: 'Show password' }));
    expect(password).toHaveAttribute('type', 'text');
    await user.click(screen.getByRole('button', { name: 'Hide password' }));
    expect(password).toHaveAttribute('type', 'password');
  });
});
