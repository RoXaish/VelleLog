import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthShell } from '../components/AuthShell';
import { useAuth } from '../auth/AuthContext';
import { ApiError } from '../lib/api';

export const AccountPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user) {
    return null;
  }

  const memberSince = new Intl.DateTimeFormat(undefined, {
    month: 'long',
    year: 'numeric',
  }).format(new Date(user.created_at));

  const handleLogout = async () => {
    setSigningOut(true);
    setError(null);
    try {
      await logout();
    } catch (logoutError) {
      setError(
        logoutError instanceof ApiError
          ? logoutError.message
          : 'Unable to sign out. Please try again.'
      );
    } finally {
      setSigningOut(false);
    }
  };

  return (
    <AuthShell
      eyebrow="Signed in"
      title="Your space."
      description="Your account is ready. Groups and weekly rhythms arrive in the next chapters."
    >
      {error && (
        <div className="form-alert form-alert--error" role="alert">
          {error}
        </div>
      )}

      <div className="account-summary">
        <span className="account-summary__label">Signed in as</span>
        <p className="account-summary__email">{user.email}</p>
        <p className="account-summary__meta">Member since {memberSince}</p>
      </div>

      <button
        type="button"
        className="btn btn--primary auth-submit"
        onClick={handleLogout}
        disabled={signingOut}
      >
        {signingOut ? 'Signing out…' : 'Sign out'}
      </button>

      <p className="auth-switch">
        <Link to="/">Back to the landing page</Link>
      </p>
    </AuthShell>
  );
};
