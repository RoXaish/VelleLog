import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { JournalShell } from '../components/JournalShell';
import { ApiError, journalApi, tagsApi, type Mood, type Tag } from '../lib/api';
import { MOOD_OPTIONS } from '../lib/moods';

interface FormErrors {
  title?: string;
  content?: string;
}

type PageStatus = 'loading' | 'ready' | 'error';

export const JournalEditorPage: React.FC = () => {
  const { entryId } = useParams();
  const navigate = useNavigate();
  const formRef = useRef<HTMLFormElement>(null);
  const isEditing = Boolean(entryId);

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [selectedMood, setSelectedMood] = useState<Mood | null>(null);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [availableTags, setAvailableTags] = useState<Tag[]>([]);
  const [newTagName, setNewTagName] = useState('');
  const [creatingTag, setCreatingTag] = useState(false);
  const [tagError, setTagError] = useState<string | null>(null);

  const [errors, setErrors] = useState<FormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<PageStatus>(isEditing ? 'loading' : 'ready');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;

    tagsApi
      .list()
      .then((tags) => {
        if (!active) return;
        setAvailableTags(tags);
      })
      .catch(() => {
        // Non-blocking for editor
      });

    if (!entryId) {
      setStatus('ready');
      return () => {
        active = false;
      };
    }

    setStatus('loading');
    setLoadError(null);

    journalApi
      .get(entryId)
      .then((entry) => {
        if (!active) return;
        setTitle(entry.title);
        setContent(entry.content);
        setSelectedMood(entry.mood);
        setSelectedTagIds(entry.tags.map((tag) => tag.id));
        setStatus('ready');
      })
      .catch((error) => {
        if (!active) return;
        setLoadError(
          error instanceof ApiError
            ? error.message
            : 'Unable to load this entry. Please try again.'
        );
        setStatus('error');
      });

    return () => {
      active = false;
    };
  }, [entryId, reloadToken]);

  const handleMoodSelect = (mood: Mood) => {
    setSelectedMood((current) => (current === mood ? null : mood));
  };

  const handleTagToggle = (tagId: number) => {
    setSelectedTagIds((current) =>
      current.includes(tagId)
        ? current.filter((id) => id !== tagId)
        : [...current, tagId]
    );
  };

  const handleCreateTag = async (event: React.MouseEvent<HTMLButtonElement> | React.KeyboardEvent<HTMLInputElement>) => {
    event.preventDefault();
    const name = newTagName.trim();
    if (!name) return;

    setCreatingTag(true);
    setTagError(null);

    try {
      const created = await tagsApi.create(name);
      setAvailableTags((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      setSelectedTagIds((current) => [...current, created.id]);
      setNewTagName('');
    } catch (error) {
      setTagError(
        error instanceof ApiError ? error.message : 'Unable to create tag.'
      );
    } finally {
      setCreatingTag(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const nextErrors: FormErrors = {};
    const trimmedTitle = title.trim();
    const trimmedContent = content.trim();

    if (!trimmedTitle) {
      nextErrors.title = 'Give this entry a title.';
    } else if (trimmedTitle.length > 200) {
      nextErrors.title = 'Keep the title to 200 characters or fewer.';
    }

    if (!trimmedContent) {
      nextErrors.content = 'Write something before saving.';
    } else if (trimmedContent.length > 50000) {
      nextErrors.content = 'This entry is too long to save.';
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSaving(true);
    setFormError(null);

    try {
      const payload = {
        title: trimmedTitle,
        content: trimmedContent,
        mood: selectedMood,
        tag_ids: selectedTagIds,
      };
      const saved = entryId
        ? await journalApi.update(entryId, payload)
        : await journalApi.create(payload);

      navigate(`/journal/${saved.id}`, { replace: true });
    } catch (error) {
      setFormError(
        error instanceof ApiError
          ? error.message
          : 'Unable to save this entry. Please try again.'
      );
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLFormElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  };

  if (status === 'loading') {
    return (
      <JournalShell>
        <div className="journal-editor-loading" role="status">
          <span className="session-spinner" aria-hidden="true" />
          <span>Opening this entry…</span>
        </div>
      </JournalShell>
    );
  }

  if (status === 'error') {
    return (
      <JournalShell>
        <div className="journal-state journal-state--error" role="alert">
          <h1>This entry could not be opened.</h1>
          <p>{loadError}</p>
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

  return (
    <JournalShell>
      <form
        ref={formRef}
        className="journal-editor"
        onSubmit={handleSubmit}
        onKeyDown={handleKeyDown}
        noValidate
        aria-busy={saving}
      >
        <header className="journal-editor__head">
          <span className="journal-eyebrow">
            {isEditing ? 'Editing entry' : 'New entry'}
          </span>
          <h1 className="journal-title">
            {isEditing ? 'Shape this page.' : 'Write it down.'}
          </h1>
          <p className="journal-description">
            {isEditing
              ? 'Make room for the thought to become clearer.'
              : 'No audience, no performance. Just the page and what you noticed.'}
          </p>
        </header>

        {formError && (
          <div className="form-alert form-alert--error" role="alert">
            {formError}
          </div>
        )}

        <div className={`journal-field${errors.title ? ' journal-field--invalid' : ''}`}>
          <label className="journal-field__label" htmlFor="entry-title">
            Title
          </label>
          <input
            id="entry-title"
            className="journal-title-input"
            type="text"
            value={title}
            onChange={(event) => {
              setTitle(event.target.value);
              if (errors.title) {
                setErrors((current) => ({ ...current, title: undefined }));
              }
              setFormError(null);
            }}
            placeholder="A title for this page"
            autoFocus
            maxLength={200}
            disabled={saving}
            aria-invalid={errors.title ? true : undefined}
            aria-describedby={errors.title ? 'entry-title-error' : undefined}
          />
          {errors.title && (
            <p id="entry-title-error" className="field__error" role="alert">
              {errors.title}
            </p>
          )}
        </div>

        <div className="editor-meta-grid">
          <div className="editor-meta-section">
            <span className="journal-field__label" id="mood-picker-label">
              Mood <span className="journal-field__optional">(optional)</span>
            </span>
            <div
              className="mood-picker"
              role="group"
              aria-labelledby="mood-picker-label"
            >
              {MOOD_OPTIONS.map(({ value, label }) => {
                const isSelected = selectedMood === value;
                return (
                  <button
                    key={value}
                    type="button"
                    className={`mood-picker__btn mood-picker__btn--${value}${isSelected ? ' is-selected' : ''}`}
                    onClick={() => handleMoodSelect(value)}
                    aria-pressed={isSelected}
                    title={label}
                  >
                    <span className="mood-badge__dot" aria-hidden="true" />
                    <span>{label}</span>
                  </button>
                );
              })}
              {selectedMood && (
                <button
                  type="button"
                  className="mood-picker__clear"
                  onClick={() => setSelectedMood(null)}
                  aria-label="Remove mood"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          <div className="editor-meta-section">
            <span className="journal-field__label" id="tag-picker-label">
              Tags <span className="journal-field__optional">(optional)</span>
            </span>
            <div
              className="tag-picker"
              role="group"
              aria-labelledby="tag-picker-label"
            >
              <div className="tag-picker__chips">
                {availableTags.map((tag) => {
                  const isSelected = selectedTagIds.includes(tag.id);
                  return (
                    <button
                      key={tag.id}
                      type="button"
                      className={`tag-picker__chip${isSelected ? ' is-selected' : ''}`}
                      onClick={() => handleTagToggle(tag.id)}
                      aria-pressed={isSelected}
                    >
                      {tag.name}
                    </button>
                  );
                })}
              </div>

              <div className="tag-picker__inline-add">
                <input
                  type="text"
                  className="tag-picker__input"
                  placeholder="New tag..."
                  value={newTagName}
                  onChange={(event) => {
                    setNewTagName(event.target.value);
                    setTagError(null);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault();
                      handleCreateTag(event);
                    }
                  }}
                  maxLength={50}
                  disabled={creatingTag}
                  aria-label="New tag name"
                />
                <button
                  type="button"
                  className="tag-picker__add-btn"
                  onClick={handleCreateTag}
                  disabled={creatingTag || !newTagName.trim()}
                >
                  {creatingTag ? '…' : '+ Add'}
                </button>
              </div>
              {tagError && (
                <p className="field__error field__error--small" role="alert">
                  {tagError}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className={`journal-field${errors.content ? ' journal-field--invalid' : ''}`}>
          <label className="journal-field__label" htmlFor="entry-content">
            Entry
          </label>
          <textarea
            id="entry-content"
            className="journal-content-input"
            value={content}
            onChange={(event) => {
              setContent(event.target.value);
              if (errors.content) {
                setErrors((current) => ({ ...current, content: undefined }));
              }
              setFormError(null);
            }}
            placeholder="Begin anywhere."
            rows={16}
            maxLength={50000}
            disabled={saving}
            aria-invalid={errors.content ? true : undefined}
            aria-describedby={errors.content ? 'entry-content-error' : undefined}
          />
          {errors.content && (
            <p id="entry-content-error" className="field__error" role="alert">
              {errors.content}
            </p>
          )}
          <span className="journal-field__count">
            {content.length.toLocaleString()} / 50,000
          </span>
        </div>

        <footer className="journal-editor__footer">
          <span className="journal-editor__hint">
            Ctrl / ⌘ + Enter to save
          </span>
          <div className="journal-editor__actions">
            <Link
              to={isEditing && entryId ? `/journal/${entryId}` : '/journal'}
              className="btn btn--ghost"
            >
              Cancel
            </Link>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={saving}
            >
              {saving ? 'Saving…' : 'Save entry'}
            </button>
          </div>
        </footer>
      </form>
    </JournalShell>
  );
};
