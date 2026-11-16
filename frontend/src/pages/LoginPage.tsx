import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthShell } from '../components/AuthShell';
import { PasswordField } from '../components/PasswordField';
import { useAuth } from '../auth/AuthContext';
import { ApiError } from '../lib/api';
import { isValidEmail, normalizeEmail } from '../lib/validation';

interface LoginLocationState {
  registered?: boolean;
  email?: string;
  from?: string;
}

interface FormErrors {
  email?: string;
  password?: string;
}

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as LoginLocationState | null) ?? {};

  const [email, setEmail] = useState(state.email ?? '');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleEmailChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(event.target.value);
    if (errors.email) setErrors((current) => ({ ...current, email: undefined }));
    setFormError(null);
  };

  const handlePasswordChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setPassword(event.target.value);
    if (errors.password) {
      setErrors((current) => ({ ...current, password: undefined }));
    }
    setFormError(null);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors: FormErrors = {};
    const trimmedEmail = email.trim();

    if (!trimmedEmail) {
      nextErrors.email = 'Enter your email address.';
    } else if (!isValidEmail(trimmedEmail)) {
      nextErrors.email = 'Enter a valid email address.';
    }

    if (!password) {
      nextErrors.password = 'Enter your password.';
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    setFormError(null);

    try {
      await login(normalizeEmail(trimmedEmail), password);
      navigate(state.from && state.from !== '/login' ? state.from : '/account', {
        replace: true,
      });
    } catch (error) {
      setFormError(
        error instanceof ApiError
          ? error.message
          : 'Unable to sign in. Please try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      eyebrow="Welcome back"
      title="Welcome back."
      description="Sign in to see your people and protect the time that matters."
    >
      {state.registered && (
        <div className="form-alert form-alert--success" role="status">
          Account created. Sign in to continue.
        </div>
      )}

      {formError && (
        <div className="form-alert form-alert--error" role="alert">
          {formError}
        </div>
      )}

      <form className="auth-form" onSubmit={handleSubmit} noValidate aria-busy={submitting}>
        <div className={`field${errors.email ? ' field--invalid' : ''}`}>
          <label className="field__label" htmlFor="login-email">
            Email
          </label>
          <input
            id="login-email"
            className="field__input"
            type="email"
            value={email}
            onChange={handleEmailChange}
            autoComplete="email"
            autoFocus
            required
            disabled={submitting}
            aria-invalid={errors.email ? true : undefined}
            aria-describedby={errors.email ? 'login-email-error' : undefined}
          />
          {errors.email && (
            <p id="login-email-error" className="field__error" role="alert">
              {errors.email}
            </p>
          )}
        </div>

        <PasswordField
          id="login-password"
          label="Password"
          value={password}
          onChange={handlePasswordChange}
          error={errors.password}
          autoComplete="current-password"
          disabled={submitting}
        />

        <button
          type="submit"
          className="btn btn--primary auth-submit"
          disabled={submitting}
        >
          {submitting ? 'Signing in…' : 'Log in'}
        </button>
      </form>

      <p className="auth-switch">
        New to Velle Log? <Link to="/signup">Create an account</Link>
      </p>
    </AuthShell>
  );
};
