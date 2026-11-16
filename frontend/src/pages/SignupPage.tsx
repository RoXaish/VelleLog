import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthShell } from '../components/AuthShell';
import { PasswordField } from '../components/PasswordField';
import { useAuth } from '../auth/AuthContext';
import { ApiError } from '../lib/api';
import { isValidEmail, normalizeEmail } from '../lib/validation';

interface FormErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
}

export const SignupPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
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

  const handleConfirmChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setConfirmPassword(event.target.value);
    if (errors.confirmPassword) {
      setErrors((current) => ({ ...current, confirmPassword: undefined }));
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
      nextErrors.password = 'Create a password.';
    } else if (password.length < 8) {
      nextErrors.password = 'Use at least 8 characters.';
    } else if (password.length > 128) {
      nextErrors.password = 'Use 128 characters or fewer.';
    }

    if (!confirmPassword) {
      nextErrors.confirmPassword = 'Confirm your password.';
    } else if (confirmPassword !== password) {
      nextErrors.confirmPassword = 'Passwords do not match.';
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    setFormError(null);

    try {
      await register(normalizeEmail(trimmedEmail), password);
      navigate('/login', {
        replace: true,
        state: { registered: true, email: normalizeEmail(trimmedEmail) },
      });
    } catch (error) {
      setFormError(
        error instanceof ApiError
          ? error.message
          : 'Unable to create your account. Please try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      eyebrow="Create account"
      title="Create your account."
      description="A quiet home for the people and plans that matter most."
    >
      {formError && (
        <div className="form-alert form-alert--error" role="alert">
          {formError}
        </div>
      )}

      <form className="auth-form" onSubmit={handleSubmit} noValidate aria-busy={submitting}>
        <div className={`field${errors.email ? ' field--invalid' : ''}`}>
          <label className="field__label" htmlFor="signup-email">
            Email
          </label>
          <input
            id="signup-email"
            className="field__input"
            type="email"
            value={email}
            onChange={handleEmailChange}
            autoComplete="email"
            autoFocus
            required
            disabled={submitting}
            aria-invalid={errors.email ? true : undefined}
            aria-describedby={errors.email ? 'signup-email-error' : undefined}
          />
          {errors.email && (
            <p id="signup-email-error" className="field__error" role="alert">
              {errors.email}
            </p>
          )}
        </div>

        <PasswordField
          id="signup-password"
          label="Password"
          value={password}
          onChange={handlePasswordChange}
          error={errors.password}
          autoComplete="new-password"
          disabled={submitting}
        />

        <PasswordField
          id="signup-confirm-password"
          label="Confirm password"
          value={confirmPassword}
          onChange={handleConfirmChange}
          error={errors.confirmPassword}
          autoComplete="new-password"
          disabled={submitting}
        />

        <button
          type="submit"
          className="btn btn--primary auth-submit"
          disabled={submitting}
        >
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="auth-switch">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </AuthShell>
  );
};
