import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { JournalShell } from '../components/JournalShell';
import { MoodBadge } from '../components/MoodBadge';
import { TagBadge } from '../components/TagBadge';
import { ApiError, journalApi, type JournalEntry } from '../lib/api';
import { formatJournalDateTime } from '../lib/journal';

type PageStatus = 'loading' | 'ready' | 'error';

export const JournalEntryPage: React.FC = () => {
  const { entryId } = useParams();
  const navigate = useNavigate();
  const cancelDeleteRef = useRef<HTMLButtonElement>(null);

  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [status, setStatus] = useState<PageStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    if (!entryId) {
      setStatus('error');
      setError('This entry could not be found.');
      return;
    }

    let active = true;
    setStatus('loading');
    setError(null);

    journalApi
      .get(entryId)
      .then((loaded) => {
        if (!active) return;
        setEntry(loaded);
        setStatus('ready');
      })
      .catch((loadError) => {
        if (!active) return;
        setError(
          loadError instanceof ApiError
            ? loadError.message
            : 'Unable to load this entry. Please try again.'
        );
        setStatus('error');
      });

    return () => {
      active = false;
    };
  }, [entryId, reloadToken]);

  useEffect(() => {
    if (!confirmingDelete) return;

    cancelDeleteRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !deleting) {
        setConfirmingDelete(false);
        setDeleteError(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [confirmingDelete, deleting]);

  const handleDelete = async () => {
    if (!entry) return;

    setDeleting(true);
    setDeleteError(null);

    try {
      await journalApi.remove(entry.id);
      navigate('/journal', { replace: true });
    } catch (deleteFailure) {
      setDeleteError(
        deleteFailure instanceof ApiError
          ? deleteFailure.message
          : 'Unable to delete this entry. Please try again.'
      );
      setDeleting(false);
    }
  };

  if (status === 'loading') {
    return (
      <JournalShell>
        <div className="journal-entry-loading" role="status">
          <span className="session-spinner" aria-hidden="true" />
          <span>Opening this entry…</span>
        </div>
      </JournalShell>
    );
  }

  if (status === 'error' || !entry) {
    return (
      <JournalShell>
        <div className="journal-state journal-state--error" role="alert">
          <h1>This entry could not be opened.</h1>
          <p>{error}</p>
          <div className="journal-state__actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setReloadToken((token) => token + 1)}
            >
              Try again
            </button>
            <Link to="/journal" className="btn btn--ghost">
              Back to journal
            </Link>
          </div>
        </div>
      </JournalShell>
    );
  }

  const wasEdited = entry.updated_at !== entry.created_at;

  return (
    <JournalShell
      actions={
        <Link to="/journal/new" className="journal-nav__cta">
          New entry
        </Link>
      }
    >
      <article className="journal-reader">
        <header className="journal-reader__head">
          <div className="journal-reader__meta">
            <Link to="/journal" className="journal-back">
              <svg width="16" height="16" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                <path
                  d="M14 9H4M8 5L4 9L8 13"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              All entries
            </Link>
            <time dateTime={entry.created_at}>
              {formatJournalDateTime(entry.created_at)}
            </time>
            {wasEdited && (
              <span className="journal-reader__edited">
                Edited {formatJournalDateTime(entry.updated_at)}
              </span>
            )}
            {entry.mood && <MoodBadge mood={entry.mood} />}
          </div>

          <h1 className="journal-reader__title">{entry.title}</h1>

          {entry.tags.length > 0 && (
            <div className="entry-tags journal-reader__tags">
              {entry.tags.map((tag) => (
                <Link key={tag.id} to={`/journal?tag_ids=${tag.id}`}>
                  <TagBadge name={tag.name} />
                </Link>
              ))}
            </div>
          )}

          <div className="journal-reader__actions">
            <Link to={`/journal/${entry.id}/edit`} className="btn btn--ghost">
              Edit entry
            </Link>
            <button
              type="button"
              className="btn btn--danger-ghost"
              onClick={() => {
                setDeleteError(null);
                setConfirmingDelete(true);
              }}
            >
              Delete
            </button>
          </div>
        </header>

        <div className="journal-reader__body">{entry.content}</div>
      </article>

      {confirmingDelete && (
        <div className="confirm-backdrop">
          <div
            className="confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-dialog-title"
            aria-describedby="delete-dialog-description"
          >
            <h2 id="delete-dialog-title">Delete this entry?</h2>
            <p id="delete-dialog-description">
              This will permanently remove “{entry.title}”. This cannot be undone.
            </p>

            {deleteError && (
              <div className="form-alert form-alert--error" role="alert">
                {deleteError}
              </div>
            )}

            <div className="confirm-dialog__actions">
              <button
                ref={cancelDeleteRef}
                type="button"
                className="btn btn--ghost"
                onClick={() => {
                  setConfirmingDelete(false);
                  setDeleteError(null);
                }}
                disabled={deleting}
              >
                Keep entry
              </button>
              <button
                type="button"
                className="btn btn--danger"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? 'Deleting…' : 'Delete entry'}
              </button>
            </div>
          </div>
        </div>
      )}
    </JournalShell>
  );
};
