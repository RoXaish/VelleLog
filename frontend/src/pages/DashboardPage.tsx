import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { JournalShell } from '../components/JournalShell';
import { MoodBadge } from '../components/MoodBadge';
import { TagBadge } from '../components/TagBadge';
import { useAuth } from '../auth/AuthContext';
import { ApiError, dashboardApi, type Dashboard } from '../lib/api';
import { formatJournalDate, journalExcerpt } from '../lib/journal';

type PageStatus = 'loading' | 'ready' | 'error';

function displayName(email: string | undefined): string {
  if (!email) return 'there';
  return email.split('@')[0] || 'there';
}

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [status, setStatus] = useState<PageStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;
    setStatus('loading');
    setError(null);

    dashboardApi
      .get()
      .then((data) => {
        if (!active) return;
        setDashboard(data);
        setStatus('ready');
      })
      .catch((loadError) => {
        if (!active) return;
        setError(
          loadError instanceof ApiError
            ? loadError.message
            : 'Unable to load your dashboard. Please try again.'
        );
        setStatus('error');
      });

    return () => {
      active = false;
    };
  }, [reloadToken]);

  return (
    <JournalShell
      actions={
        <Link to="/journal/new" className="journal-nav__cta">
          New entry
        </Link>
      }
    >
      <section className="dashboard-hero" aria-labelledby="dashboard-heading">
        <div className="dashboard-hero__copy">
          <span className="journal-eyebrow">Your writing life</span>
          <h1 id="dashboard-heading" className="journal-title dashboard-title">
            Welcome back, {displayName(user?.email)}.
          </h1>
          <p className="journal-description">
            A small record of your days, gathered in one quiet place. Come back
            to a thought, notice a pattern, or simply begin again.
          </p>
          <div className="dashboard-hero__actions">
            <Link to="/journal/new" className="btn btn--primary">
              Write a new entry
            </Link>
            <Link to="/journal" className="btn btn--ghost">
              Browse your journal
            </Link>
          </div>
        </div>

        <div className="dashboard-hero__mark" aria-hidden="true">
          <span className="dashboard-hero__mark-line" />
          <span className="dashboard-hero__mark-word">Velle</span>
          <span className="dashboard-hero__mark-line" />
        </div>
      </section>

      {status === 'loading' && (
        <div className="dashboard-loading" role="status" aria-label="Loading dashboard">
          <div className="dashboard-loading__stats">
            {[0, 1, 2].map((item) => (
              <span key={item} />
            ))}
          </div>
          <div className="dashboard-loading__rows">
            {[0, 1, 2].map((item) => (
              <span key={item} />
            ))}
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="journal-state journal-state--error" role="alert">
          <h2>Your dashboard could not be loaded.</h2>
          <p>{error}</p>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setReloadToken((token) => token + 1)}
          >
            Try again
          </button>
        </div>
      )}

      {status === 'ready' && dashboard && (
        <>
          <section className="dashboard-stats" aria-label="Writing statistics">
            <div className="dashboard-stat">
              <span className="dashboard-stat__value">
                {dashboard.total_entries}
              </span>
              <span className="dashboard-stat__label">Total entries</span>
            </div>
            <div className="dashboard-stat">
              <span className="dashboard-stat__value">
                {dashboard.entries_this_week}
              </span>
              <span className="dashboard-stat__label">This week</span>
            </div>
            <div className="dashboard-stat dashboard-stat--streak">
              <span className="dashboard-stat__value">
                {dashboard.current_streak}
              </span>
              <span className="dashboard-stat__label">
                Day streak
              </span>
              <span className="dashboard-stat__hint">
                {dashboard.current_streak > 0
                  ? 'Keep the thread going.'
                  : 'A single entry starts it.'}
              </span>
            </div>
          </section>

          {dashboard.total_entries === 0 ? (
            <section className="dashboard-empty">
              <span className="journal-state__mark" aria-hidden="true">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M6 4.5H16.5L19 7V19.5H6V4.5Z"
                    stroke="currentColor"
                    strokeWidth="1.4"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M9 9.5H16M9 13H16M9 16.5H13.5"
                    stroke="currentColor"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                  />
                </svg>
              </span>
              <h2>Your first page is waiting.</h2>
              <p>
                There is nothing to catch up on yet. Start with one sentence
                about today and let the rest arrive when it does.
              </p>
              <Link to="/journal/new" className="btn btn--primary">
                Write your first entry
              </Link>
            </section>
          ) : (
            <section
              className="dashboard-recent"
              aria-labelledby="dashboard-recent-heading"
            >
              <div className="dashboard-section-head">
                <div>
                  <span className="journal-eyebrow">Lately</span>
                  <h2 id="dashboard-recent-heading">Recent entries</h2>
                </div>
                <Link to="/journal" className="dashboard-section-head__link">
                  View all
                </Link>
              </div>

              <ul className="dashboard-entry-list">
                {dashboard.recent_entries.map((entry) => (
                  <li key={entry.id}>
                    <Link
                      to={`/journal/${entry.id}`}
                      className="dashboard-entry"
                    >
                      <div className="dashboard-entry__top">
                        <time dateTime={entry.created_at}>
                          {formatJournalDate(entry.created_at)}
                        </time>
                        {entry.mood && <MoodBadge mood={entry.mood} compact />}
                      </div>
                      <h3>{entry.title}</h3>
                      <p>{journalExcerpt(entry.content, 130)}</p>
                      {entry.tags.length > 0 && (
                        <div className="entry-tags">
                          {entry.tags.map((tag) => (
                            <TagBadge key={tag.id} name={tag.name} />
                          ))}
                        </div>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </JournalShell>
  );
};
