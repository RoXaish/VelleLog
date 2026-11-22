import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { JournalShell } from '../components/JournalShell';
import { ApiError, tagsApi, type Tag } from '../lib/api';

type PageStatus = 'loading' | 'ready' | 'error';

export const TagsPage: React.FC = () => {
  const [tags, setTags] = useState<Tag[]>([]);
  const [status, setStatus] = useState<PageStatus>('loading');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState('');
  const [savingTagId, setSavingTagId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [confirmTag, setConfirmTag] = useState<Tag | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const cancelDeleteRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let active = true;
    setStatus('loading');
    setLoadError(null);

    tagsApi
      .list()
      .then((data) => {
        if (!active) return;
        setTags(data);
        setStatus('ready');
      })
      .catch((error) => {
        if (!active) return;
        setLoadError(
          error instanceof ApiError
            ? error.message
            : 'Unable to load your tags. Please try again.'
        );
        setStatus('error');
      });

    return () => {
      active = false;
    };
  }, [reloadToken]);

  useEffect(() => {
    if (!confirmTag) return;

    cancelDeleteRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !deleting) {
        setConfirmTag(null);
        setDeleteError(null);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [confirmTag, deleting]);

  const refreshTags = async () => {
    const data = await tagsApi.list();
    setTags(data);
  };

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const name = newName.trim();
    if (!name) {
      setCreateError('Give the tag a name.');
      return;
    }

    setCreating(true);
    setCreateError(null);

    try {
      await tagsApi.create(name);
      setNewName('');
      await refreshTags();
    } catch (error) {
      setCreateError(
        error instanceof ApiError
          ? error.message
          : 'Unable to create this tag. Please try again.'
      );
    } finally {
      setCreating(false);
    }
  };

  const startRename = (tag: Tag) => {
    setEditingId(tag.id);
    setEditingName(tag.name);
    setActionError(null);
  };

  const cancelRename = () => {
    setEditingId(null);
    setEditingName('');
    setActionError(null);
  };

  const handleRename = async (event: React.FormEvent<HTMLFormElement>, tag: Tag) => {
    event.preventDefault();
    const name = editingName.trim();
    if (!name) {
      setActionError('Give the tag a name.');
      return;
    }

    setSavingTagId(tag.id);
    setActionError(null);

    try {
      const updated = await tagsApi.update(tag.id, name);
      setTags((current) =>
        current
          .map((item) => (item.id === updated.id ? updated : item))
          .sort((a, b) => a.name.localeCompare(b.name))
      );
      setEditingId(null);
      setEditingName('');
    } catch (error) {
      setActionError(
        error instanceof ApiError
          ? error.message
          : 'Unable to rename this tag. Please try again.'
      );
    } finally {
      setSavingTagId(null);
    }
  };

  const handleDelete = async () => {
    if (!confirmTag) return;

    setDeleting(true);
    setDeleteError(null);

    try {
      await tagsApi.remove(confirmTag.id);
      setTags((current) => current.filter((tag) => tag.id !== confirmTag.id));
      setConfirmTag(null);
    } catch (error) {
      setDeleteError(
        error instanceof ApiError
          ? error.message
          : 'Unable to delete this tag. Please try again.'
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <JournalShell
      actions={
        <Link to="/journal/new" className="journal-nav__cta">
          New entry
        </Link>
      }
    >
      <section className="journal-intro" aria-labelledby="tags-heading">
        <div className="journal-intro__copy">
          <span className="journal-eyebrow">Your vocabulary</span>
          <h1 id="tags-heading" className="journal-title">
            Tags.
          </h1>
          <p className="journal-description">
            Gentle labels for the themes that recur in your writing. Use them to
            gather related days, moods, and thoughts.
          </p>
        </div>
        <div className="journal-intro__meta">
          <span className="journal-count">
            {tags.length} {tags.length === 1 ? 'tag' : 'tags'}
          </span>
        </div>
      </section>

      <form className="tag-create" onSubmit={handleCreate} noValidate>
        <label className="journal-field__label" htmlFor="new-tag-name">
          New tag
        </label>
        <div className="tag-create__row">
          <input
            id="new-tag-name"
            className="tag-input"
            type="text"
            value={newName}
            onChange={(event) => {
              setNewName(event.target.value);
              setCreateError(null);
            }}
            placeholder="e.g. Reflection"
            maxLength={50}
            disabled={creating}
            aria-invalid={createError ? true : undefined}
            aria-describedby={createError ? 'new-tag-error' : undefined}
          />
          <button
            type="submit"
            className="btn btn--primary tag-create__button"
            disabled={creating}
          >
            {creating ? 'Creating…' : 'Create tag'}
          </button>
        </div>
        {createError && (
          <p id="new-tag-error" className="field__error" role="alert">
            {createError}
          </p>
        )}
      </form>

      {actionError && (
        <div className="form-alert form-alert--error" role="alert">
          {actionError}
        </div>
      )}

      {status === 'loading' && (
        <div className="journal-editor-loading" role="status">
          <span className="session-spinner" aria-hidden="true" />
          <span>Gathering your tags…</span>
        </div>
      )}

      {status === 'error' && (
        <div className="journal-state journal-state--error" role="alert">
          <h2>Your tags could not be loaded.</h2>
          <p>{loadError}</p>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setReloadToken((token) => token + 1)}
          >
            Try again
          </button>
        </div>
      )}

      {status === 'ready' && tags.length === 0 && (
        <div className="journal-state">
          <h2>No tags yet.</h2>
          <p>
            Add a few words for the themes you return to. You can attach them to
            any entry as you write.
          </p>
        </div>
      )}

      {status === 'ready' && tags.length > 0 && (
        <ul className="tag-list" aria-label="Your tags">
          {tags.map((tag) => (
            <li key={tag.id} className="tag-item">
              {editingId === tag.id ? (
                <form
                  className="tag-item__edit"
                  onSubmit={(event) => handleRename(event, tag)}
                  noValidate
                >
                  <input
                    className="tag-input"
                    type="text"
                    value={editingName}
                    onChange={(event) => {
                      setEditingName(event.target.value);
                      setActionError(null);
                    }}
                    aria-label={`Rename ${tag.name}`}
                    maxLength={50}
                    autoFocus
                    disabled={savingTagId === tag.id}
                  />
                  <button
                    type="submit"
                    className="tag-item__button tag-item__button--save"
                    disabled={savingTagId === tag.id}
                  >
                    {savingTagId === tag.id ? 'Saving…' : 'Save'}
                  </button>
                  <button
                    type="button"
                    className="tag-item__button"
                    onClick={cancelRename}
                    disabled={savingTagId === tag.id}
                  >
                    Cancel
                  </button>
                </form>
              ) : (
                <>
                  <div className="tag-item__identity">
                    <span className="tag-item__name">{tag.name}</span>
                    <span className="tag-item__count">
                      {tag.entry_count}{' '}
                      {tag.entry_count === 1 ? 'entry' : 'entries'}
                    </span>
                  </div>
                  <div className="tag-item__actions">
                    <button
                      type="button"
                      className="tag-item__button"
                      onClick={() => startRename(tag)}
                    >
                      Rename
                    </button>
                    <button
                      type="button"
                      className="tag-item__button tag-item__button--danger"
                      onClick={() => {
                        setDeleteError(null);
                        setConfirmTag(tag);
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {confirmTag && (
        <div className="confirm-backdrop">
          <div
            className="confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-tag-dialog-title"
            aria-describedby="delete-tag-dialog-description"
          >
            <h2 id="delete-tag-dialog-title">Delete this tag?</h2>
            <p id="delete-tag-dialog-description">
              “{confirmTag.name}” will be removed from your tags. Entries using
              it will stay exactly as they are.
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
                  setConfirmTag(null);
                  setDeleteError(null);
                }}
                disabled={deleting}
              >
                Keep tag
              </button>
              <button
                type="button"
                className="btn btn--danger"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? 'Deleting…' : 'Delete tag'}
              </button>
            </div>
          </div>
        </div>
      )}
    </JournalShell>
  );
};
