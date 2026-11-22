import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { JournalShell } from '../components/JournalShell';
import { MoodBadge } from '../components/MoodBadge';
import { TagBadge } from '../components/TagBadge';
import { ApiError, journalApi, tagsApi, type JournalEntry, type Mood, type Tag } from '../lib/api';
import { formatJournalDate, journalExcerpt } from '../lib/journal';
import { MOOD_OPTIONS } from '../lib/moods';

const PAGE_SIZE = 10;

type PageStatus = 'loading' | 'ready' | 'error';

export const JournalPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const initialTagId = searchParams.get('tag_ids')
    ? Number(searchParams.get('tag_ids'))
    : null;
  const initialMood = (searchParams.get('mood') as Mood) || null;

  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedMood, setSelectedMood] = useState<Mood | null>(initialMood);
  const [selectedTagId, setSelectedTagId] = useState<number | null>(
    Number.isFinite(initialTagId) ? initialTagId : null
  );
  const [status, setStatus] = useState<PageStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;
    tagsApi
      .list()
      .then((data) => {
        if (!active) return;
        setTags(data);
      })
      .catch(() => {
        // Non-blocking
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setDebouncedSearch(search.trim());
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [search]);

  useEffect(() => {
    let active = true;
    setStatus('loading');
    setError(null);

    journalApi
      .list({
        page,
        pageSize: PAGE_SIZE,
        search: debouncedSearch,
        tagIds: selectedTagId ? [selectedTagId] : [],
        mood: selectedMood,
      })
      .then((response) => {
        if (!active) return;
        setEntries(response.items);
        setTotal(response.total);
        setTotalPages(response.total_pages);
        setStatus('ready');
      })
      .catch((loadError) => {
        if (!active) return;
        setError(
          loadError instanceof ApiError
            ? loadError.message
            : 'Unable to load your journal. Please try again.'
        );
        setStatus('error');
      });

    return () => {
      active = false;
    };
  }, [page, debouncedSearch, selectedTagId, selectedMood, reloadToken]);

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(event.target.value);
    setPage(1);
  };

  const handleMoodFilter = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = (event.target.value as Mood) || null;
    setSelectedMood(value);
    setPage(1);
  };

  const handleTagFilter = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value ? Number(event.target.value) : null;
    setSelectedTagId(value);
    setPage(1);
  };

  const clearAllFilters = () => {
    setSearch('');
    setDebouncedSearch('');
    setSelectedMood(null);
    setSelectedTagId(null);
    setSearchParams({});
    setPage(1);
  };

  const isSearching = debouncedSearch.length > 0;
  const isFiltering =
    isSearching || selectedMood !== null || selectedTagId !== null;
  const showEmptyState = status === 'ready' && entries.length === 0;

  return (
    <JournalShell
      actions={
        <Link to="/journal/new" className="journal-nav__cta">
          New entry
        </Link>
      }
    >
      <section className="journal-intro" aria-labelledby="journal-heading">
        <div className="journal-intro__copy">
          <span className="journal-eyebrow">Your private pages</span>
          <h1 id="journal-heading" className="journal-title">
            Your journal.
          </h1>
          <p className="journal-description">
            A quiet place to think out loud, remember the small things, and keep
            a record of your days.
          </p>
        </div>

        <div className="journal-intro__meta">
          <span className="journal-count">
            {total} {total === 1 ? 'entry' : 'entries'}
          </span>
          <Link to="/journal/new" className="btn btn--primary journal-new">
            Write a new entry
          </Link>
        </div>
      </section>

      <div className="journal-toolbar">
        <div className="journal-toolbar__search">
          <label className="journal-search">
            <svg
              width="17"
              height="17"
              viewBox="0 0 20 20"
              fill="none"
              aria-hidden="true"
            >
              <circle
                cx="8.6"
                cy="8.6"
                r="5.4"
                stroke="currentColor"
                strokeWidth="1.5"
              />
              <path
                d="M12.8 12.8L16.5 16.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            <input
              type="search"
              value={search}
              onChange={handleSearchChange}
              placeholder="Search titles and words"
              aria-label="Search entries"
            />
          </label>
          {isSearching && (
            <span className="journal-search__hint">
              Results for “{debouncedSearch}”
            </span>
          )}
        </div>

        <div className="journal-toolbar__filters">
          <select
            className="journal-select"
            value={selectedMood ?? ''}
            onChange={handleMoodFilter}
            aria-label="Filter by mood"
          >
            <option value="">All moods</option>
            {MOOD_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>

          <select
            className="journal-select"
            value={selectedTagId ?? ''}
            onChange={handleTagFilter}
            aria-label="Filter by tag"
          >
            <option value="">All tags</option>
            {tags.map((tag) => (
              <option key={tag.id} value={tag.id}>
                #{tag.name}
              </option>
            ))}
          </select>

          {isFiltering && (
            <button
              type="button"
              className="journal-toolbar__clear"
              onClick={clearAllFilters}
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {status === 'loading' && (
        <div className="journal-skeletons" role="status" aria-label="Loading entries">
          {[0, 1, 2].map((item) => (
            <div className="journal-skeleton" key={item}>
              <span className="journal-skeleton__date" />
              <span className="journal-skeleton__lines">
                <span />
                <span />
              </span>
            </div>
          ))}
        </div>
      )}

      {status === 'error' && (
        <div className="journal-state journal-state--error" role="alert">
          <h2>Your journal could not be loaded.</h2>
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

      {showEmptyState && !isFiltering && (
        <div className="journal-state">
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
          <h2>Nothing written yet.</h2>
          <p>
            Start with a sentence. A thought, a memory, a small observation from
            today.
          </p>
          <Link to="/journal/new" className="btn btn--primary">
            Write your first entry
          </Link>
        </div>
      )}

      {showEmptyState && isFiltering && (
        <div className="journal-state">
          <h2>No entries found.</h2>
          <p>Try different keywords or filters to see your entries.</p>
          <button type="button" className="btn btn--ghost" onClick={clearAllFilters}>
            Clear filters
          </button>
        </div>
      )}

      {status === 'ready' && entries.length > 0 && (
        <ul className="journal-list">
          {entries.map((entry) => (
            <li key={entry.id}>
              <Link to={`/journal/${entry.id}`} className="journal-entry">
                <time
                  className="journal-entry__date"
                  dateTime={entry.created_at}
                >
                  {formatJournalDate(entry.created_at)}
                </time>
                <span className="journal-entry__body">
                  <span className="journal-entry__head-row">
                    <h2 className="journal-entry__title">{entry.title}</h2>
                    {entry.mood && <MoodBadge mood={entry.mood} compact />}
                  </span>
                  <span className="journal-entry__excerpt">
                    {journalExcerpt(entry.content)}
                  </span>
                  {entry.tags.length > 0 && (
                    <span className="entry-tags journal-entry__tags">
                      {entry.tags.map((tag) => (
                        <TagBadge key={tag.id} name={tag.name} />
                      ))}
                    </span>
                  )}
                </span>
                <span className="journal-entry__arrow" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                    <path
                      d="M4 9H14M10 5L14 9L10 13"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {status === 'ready' && totalPages > 1 && (
        <nav className="journal-pagination" aria-label="Journal pages">
          <button
            type="button"
            className="journal-pagination__button"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page <= 1}
          >
            Previous
          </button>
          <span className="journal-pagination__status">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            className="journal-pagination__button"
            onClick={() =>
              setPage((current) => Math.min(totalPages, current + 1))
            }
            disabled={page >= totalPages}
          >
            Next
          </button>
        </nav>
      )}
    </JournalShell>
  );
};
