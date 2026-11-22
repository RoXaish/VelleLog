import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import {
  installFetchMock,
  jsonResponse,
  requestHeaders,
  requestMethod,
  requestPath,
} from '../test/api';
import { renderApp } from '../test/renderApp';
import type { JournalEntry, JournalEntryList } from '../lib/api';

const USER = {
  id: 1,
  email: 'journal@example.com',
  created_at: '2026-11-01T10:00:00',
  updated_at: '2026-11-01T10:00:00',
};

const MORNING_ENTRY: JournalEntry = {
  id: 1,
  user_id: 1,
  title: 'Morning Pages',
  content:
    'The light came through the window before the city woke up. Coffee, quiet, and a blank page.',
  mood: 'calm',
  tags: [{ id: 1, name: 'Morning' }],
  created_at: '2026-11-20T08:00:00',
  updated_at: '2026-11-20T08:00:00',
};

const RAIN_ENTRY: JournalEntry = {
  id: 2,
  user_id: 1,
  title: 'Afternoon',
  content: 'The rain stayed against the window for hours.',
  mood: 'sad',
  tags: [{ id: 2, name: 'Weather' }],
  created_at: '2026-11-19T15:00:00',
  updated_at: '2026-11-19T15:00:00',
};

function listResponse(
  items: JournalEntry[],
  overrides: Partial<JournalEntryList> = {}
): JournalEntryList {
  const total = overrides.total ?? items.length;
  const page = overrides.page ?? 1;
  const pageSize = overrides.page_size ?? 10;
  const totalPages =
    overrides.total_pages ?? (total === 0 ? 0 : Math.ceil(total / pageSize));

  return {
    items,
    total,
    page,
    page_size: pageSize,
    total_pages: totalPages,
    has_next: page < totalPages,
    has_previous: page > 1,
    ...overrides,
  };
}

function isAuthMe(input: RequestInfo | URL): boolean {
  return requestPath(input).endsWith('/api/auth/me');
}

function isJournalList(input: RequestInfo | URL, init?: RequestInit): boolean {
  return (
    requestPath(input).includes('/api/journal-entries?') &&
    requestMethod(init) === 'GET'
  );
}

function journalEntryPath(input: RequestInfo | URL): string {
  return requestPath(input).split('?')[0];
}

describe('journal', () => {
  it('redirects anonymous visitors to login', async () => {
    installFetchMock((input) => {
      if (isAuthMe(input)) {
        return jsonResponse({ detail: 'Could not validate credentials' }, 401);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal');

    expect(
      await screen.findByRole('heading', { name: 'Welcome back.' })
    ).toBeInTheDocument();
  });

  it('lists entries newest first with count and links', async () => {
    installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      if (isJournalList(input, init)) {
        return jsonResponse(listResponse([MORNING_ENTRY, RAIN_ENTRY]));
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal');

    expect(
      await screen.findByRole('heading', { name: 'Your journal.' })
    ).toBeInTheDocument();
    expect(
      await screen.findByRole('heading', { name: 'Morning Pages' })
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Afternoon' })).toBeInTheDocument();
    expect(screen.getByText('2 entries')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Write a new entry' })
    ).toHaveAttribute('href', '/journal/new');
    expect(
      screen.getByRole('link', { name: /Morning Pages/ })
    ).toHaveAttribute('href', '/journal/1');
  });

  it('searches titles and content after a short pause', async () => {
    const fetchMock = installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      if (isJournalList(input, init)) {
        const url = new URL(requestPath(input), 'http://localhost');
        if (url.searchParams.get('search') === 'rain') {
          return jsonResponse(listResponse([RAIN_ENTRY]));
        }
        return jsonResponse(listResponse([MORNING_ENTRY, RAIN_ENTRY]));
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal');
    await screen.findByRole('heading', { name: 'Morning Pages' });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Search entries'), 'rain');

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          requestPath(input).includes('search=rain')
        )
      ).toBe(true);
    });

    expect(
      await screen.findByRole('heading', { name: 'Afternoon' })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { name: 'Morning Pages' })
    ).not.toBeInTheDocument();
    expect(screen.getByText(/Results for/)).toBeInTheDocument();
  });

  it('shows an empty state for a new journal', async () => {
    installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      if (isJournalList(input, init)) {
        return jsonResponse(listResponse([]));
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal');

    expect(
      await screen.findByRole('heading', { name: 'Nothing written yet.' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Write your first entry' })
    ).toHaveAttribute('href', '/journal/new');
  });

  it('moves between pages', async () => {
    installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      if (isJournalList(input, init)) {
        const url = new URL(requestPath(input), 'http://localhost');
        const page = Number(url.searchParams.get('page') ?? '1');
        if (page === 2) {
          const older = { ...RAIN_ENTRY, id: 3, title: 'Older entry' };
          return jsonResponse(
            listResponse([older], {
              total: 12,
              page: 2,
              total_pages: 2,
            })
          );
        }
        return jsonResponse(
          listResponse([MORNING_ENTRY], {
            total: 12,
            page: 1,
            total_pages: 2,
          })
        );
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal');
    await screen.findByRole('heading', { name: 'Morning Pages' });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Next' }));

    expect(
      await screen.findByRole('heading', { name: 'Older entry' })
    ).toBeInTheDocument();
    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeEnabled();
  });

  it('validates and creates an entry with CSRF protection', async () => {
    document.cookie = 'velle_csrf_token=test-csrf-token; path=/';
    const created: JournalEntry = {
      ...MORNING_ENTRY,
      id: 3,
      title: 'A new memory',
      content: 'A small moment worth keeping.',
    };

    const fetchMock = installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      if (
        requestMethod(init) === 'POST' &&
        journalEntryPath(input).endsWith('/api/journal-entries')
      ) {
        return jsonResponse(created, 201);
      }
      if (
        requestMethod(init) === 'GET' &&
        journalEntryPath(input).endsWith('/api/journal-entries/3')
      ) {
        return jsonResponse(created);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal/new');
    expect(
      await screen.findByRole('heading', { name: 'Write it down.' })
    ).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Save entry' }));

    expect(screen.getByText('Give this entry a title.')).toBeInTheDocument();
    expect(screen.getByText('Write something before saving.')).toBeInTheDocument();

    await user.type(screen.getByLabelText('Title'), '  A new memory  ');
    await user.type(
      screen.getByLabelText('Entry'),
      '  A small moment worth keeping.  '
    );
    await user.click(screen.getByRole('button', { name: 'Save entry' }));

    expect(
      await screen.findByRole('heading', { name: 'A new memory' })
    ).toBeInTheDocument();
    expect(screen.getByText('A small moment worth keeping.')).toBeInTheDocument();

    const postCall = fetchMock.mock.calls.find(
      ([input, init]) =>
        requestMethod(init) === 'POST' &&
        journalEntryPath(input).endsWith('/api/journal-entries')
    );
    expect(postCall).toBeDefined();
    expect(JSON.parse(String(postCall?.[1]?.body))).toEqual({
      title: 'A new memory',
      content: 'A small moment worth keeping.',
      mood: null,
      tag_ids: [],
    });
    expect(requestHeaders(postCall?.[1]).get('X-CSRF-Token')).toBe(
      'test-csrf-token'
    );
  });

  it('prefills and updates an existing entry', async () => {
    let current = MORNING_ENTRY;

    installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      if (
        requestMethod(init) === 'GET' &&
        journalEntryPath(input).endsWith('/api/journal-entries/1')
      ) {
        return jsonResponse(current);
      }
      if (
        requestMethod(init) === 'PATCH' &&
        journalEntryPath(input).endsWith('/api/journal-entries/1')
      ) {
        const payload = JSON.parse(String(init?.body));
        current = {
          ...current,
          ...payload,
          updated_at: '2026-11-21T09:30:00',
        };
        return jsonResponse(current);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal/1/edit');

    const titleInput = await screen.findByLabelText('Title');
    expect(titleInput).toHaveValue('Morning Pages');
    expect(screen.getByLabelText('Entry')).toHaveValue(MORNING_ENTRY.content);

    const user = userEvent.setup();
    await user.clear(titleInput);
    await user.type(titleInput, 'A clearer morning');
    await user.click(screen.getByRole('button', { name: 'Save entry' }));

    expect(
      await screen.findByRole('heading', { name: 'A clearer morning' })
    ).toBeInTheDocument();
  });

  it('confirms before deleting and returns to the journal', async () => {
    let deleted = false;

    const fetchMock = installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      if (
        requestMethod(init) === 'GET' &&
        journalEntryPath(input).endsWith('/api/journal-entries/1')
      ) {
        return jsonResponse(MORNING_ENTRY);
      }
      if (
        requestMethod(init) === 'DELETE' &&
        journalEntryPath(input).endsWith('/api/journal-entries/1')
      ) {
        deleted = true;
        return new Response(null, { status: 204 });
      }
      if (isJournalList(input, init)) {
        return jsonResponse(listResponse(deleted ? [] : [MORNING_ENTRY]));
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal/1');
    expect(
      await screen.findByRole('heading', { name: 'Morning Pages' })
    ).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    const dialog = screen.getByRole('dialog', { name: 'Delete this entry?' });
    expect(within(dialog).getByText(/permanently remove/)).toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: 'Keep entry' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Delete' }));
    await user.click(screen.getByRole('button', { name: 'Delete entry' }));

    expect(
      await screen.findByRole('heading', { name: 'Nothing written yet.' })
    ).toBeInTheDocument();

    const deleteCall = fetchMock.mock.calls.find(
      ([input, init]) =>
        requestMethod(init) === 'DELETE' &&
        journalEntryPath(input).endsWith('/api/journal-entries/1')
    );
    expect(deleteCall).toBeDefined();
  });

  it('shows an error state and retries loading the list', async () => {
    let attempts = 0;

    installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      if (isJournalList(input, init)) {
        attempts += 1;
        if (attempts === 1) {
          return jsonResponse({ detail: 'The archive is unavailable.' }, 500);
        }
        return jsonResponse(listResponse([MORNING_ENTRY]));
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal');

    expect(
      await screen.findByRole('heading', {
        name: 'Your journal could not be loaded.',
      })
    ).toBeInTheDocument();
    expect(screen.getByText('The archive is unavailable.')).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Try again' }));

    expect(
      await screen.findByRole('heading', { name: 'Morning Pages' })
    ).toBeInTheDocument();
  });

  it('displays personalized dashboard with streak, writing stats, and recent entries', async () => {
    installFetchMock((input) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      if (requestPath(input).endsWith('/api/dashboard')) {
        return jsonResponse({
          total_entries: 7,
          entries_this_week: 3,
          current_streak: 5,
          recent_entries: [MORNING_ENTRY],
        });
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/dashboard');

    expect(
      await screen.findByRole('heading', { name: /Welcome back, journal/ })
    ).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('Total entries')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('This week')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Day streak')).toBeInTheDocument();
    expect(screen.getByText('Morning Pages')).toBeInTheDocument();
    expect(screen.getByText('Calm')).toBeInTheDocument();
    expect(screen.getByText('Morning')).toBeInTheDocument();
  });

  it('manages tags on the tags page: creates, renames, and deletes', async () => {
    document.cookie = 'velle_csrf_token=test-csrf-token; path=/';
    let tagsList = [
      { id: 1, user_id: 1, name: 'Morning', entry_count: 2, created_at: '2026-11-20T08:00:00', updated_at: '2026-11-20T08:00:00' },
    ];

    installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      const path = requestPath(input);
      const method = requestMethod(init);

      if (path.endsWith('/api/tags') && method === 'GET') {
        return jsonResponse(tagsList);
      }
      if (path.endsWith('/api/tags') && method === 'POST') {
        const body = JSON.parse(String(init?.body));
        const newTag = {
          id: 2,
          user_id: 1,
          name: body.name,
          entry_count: 0,
          created_at: '2026-11-22T10:00:00',
          updated_at: '2026-11-22T10:00:00',
        };
        tagsList.push(newTag);
        return jsonResponse(newTag, 201);
      }
      if (path.endsWith('/api/tags/1') && method === 'PATCH') {
        const body = JSON.parse(String(init?.body));
        tagsList[0] = { ...tagsList[0], name: body.name };
        return jsonResponse(tagsList[0]);
      }
      if (path.endsWith('/api/tags/1') && method === 'DELETE') {
        tagsList = tagsList.filter((t) => t.id !== 1);
        return new Response(null, { status: 204 });
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/tags');

    expect(await screen.findByRole('heading', { name: 'Tags.' })).toBeInTheDocument();
    expect(screen.getByText('Morning')).toBeInTheDocument();
    expect(screen.getByText('2 entries')).toBeInTheDocument();

    const user = userEvent.setup();

    // Create tag
    await user.type(screen.getByLabelText('New tag'), 'Evening');
    await user.click(screen.getByRole('button', { name: 'Create tag' }));
    expect(await screen.findByText('Evening')).toBeInTheDocument();

    // Rename tag
    const renameButtons = screen.getAllByRole('button', { name: 'Rename' });
    await user.click(renameButtons[0]);
    const renameInput = screen.getByLabelText('Rename Morning');
    await user.clear(renameInput);
    await user.type(renameInput, 'Early Morning');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText('Early Morning')).toBeInTheDocument();

    // Delete tag
    const deleteButtons = screen.getAllByRole('button', { name: 'Delete' });
    await user.click(deleteButtons[0]);
    const dialog = screen.getByRole('dialog', { name: 'Delete this tag?' });
    expect(within(dialog).getByText(/will be removed/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Delete tag' }));
    await waitFor(() => {
      expect(screen.queryByText('Early Morning')).not.toBeInTheDocument();
    });
  });

  it('selects mood and tags while creating and editing an entry', async () => {
    document.cookie = 'velle_csrf_token=test-csrf-token; path=/';
    const tagList = [
      { id: 1, user_id: 1, name: 'Morning', entry_count: 1, created_at: '2026-11-20T08:00:00', updated_at: '2026-11-20T08:00:00' },
      { id: 2, user_id: 1, name: 'Nature', entry_count: 0, created_at: '2026-11-20T08:00:00', updated_at: '2026-11-20T08:00:00' },
    ];

    const createdWithMood: JournalEntry = {
      ...MORNING_ENTRY,
      id: 10,
      title: 'Sunrise Walk',
      content: 'Clear air and grateful thoughts.',
      mood: 'grateful',
      tags: [{ id: 1, name: 'Morning' }],
    };

    const fetchMock = installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      const path = requestPath(input);
      const method = requestMethod(init);

      if (path.endsWith('/api/tags') && method === 'GET') {
        return jsonResponse(tagList);
      }
      if (path.endsWith('/api/journal-entries') && method === 'POST') {
        return jsonResponse(createdWithMood, 201);
      }
      if (path.endsWith('/api/journal-entries/10') && method === 'GET') {
        return jsonResponse(createdWithMood);
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal/new');
    expect(await screen.findByRole('heading', { name: 'Write it down.' })).toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Title'), 'Sunrise Walk');
    await user.type(screen.getByLabelText('Entry'), 'Clear air and grateful thoughts.');

    // Select mood: Grateful
    await user.click(screen.getByRole('button', { name: 'Grateful' }));

    // Select tag: Morning
    await user.click(await screen.findByRole('button', { name: 'Morning' }));

    await user.click(screen.getByRole('button', { name: 'Save entry' }));

    expect(await screen.findByRole('heading', { name: 'Sunrise Walk' })).toBeInTheDocument();
    expect(screen.getByText('Grateful')).toBeInTheDocument();
    expect(screen.getByText('Morning')).toBeInTheDocument();

    const postCall = fetchMock.mock.calls.find(
      ([input, init]) =>
        requestMethod(init) === 'POST' &&
        journalEntryPath(input).endsWith('/api/journal-entries')
    );
    expect(postCall).toBeDefined();
    expect(JSON.parse(String(postCall?.[1]?.body))).toEqual({
      title: 'Sunrise Walk',
      content: 'Clear air and grateful thoughts.',
      mood: 'grateful',
      tag_ids: [1],
    });
  });

  it('filters entries by mood and tag', async () => {
    const tagList = [
      { id: 1, user_id: 1, name: 'Morning', entry_count: 1, created_at: '2026-11-20T08:00:00', updated_at: '2026-11-20T08:00:00' },
      { id: 2, user_id: 1, name: 'Weather', entry_count: 1, created_at: '2026-11-20T08:00:00', updated_at: '2026-11-20T08:00:00' },
    ];

    const fetchMock = installFetchMock((input, init) => {
      if (isAuthMe(input)) return jsonResponse(USER);
      const path = requestPath(input);
      if (path.endsWith('/api/tags')) return jsonResponse(tagList);
      if (isJournalList(input, init)) {
        const url = new URL(path, 'http://localhost');
        const moodParam = url.searchParams.get('mood');
        const tagParam = url.searchParams.get('tag_ids');

        if (moodParam === 'calm') {
          return jsonResponse(listResponse([MORNING_ENTRY]));
        }
        if (tagParam === '2') {
          return jsonResponse(listResponse([RAIN_ENTRY]));
        }
        return jsonResponse(listResponse([MORNING_ENTRY, RAIN_ENTRY]));
      }
      return jsonResponse({ detail: 'Not found' }, 404);
    });

    renderApp('/journal');
    expect(await screen.findByRole('heading', { name: 'Morning Pages' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Afternoon' })).toBeInTheDocument();

    const user = userEvent.setup();

    // Filter by mood: Calm
    await user.selectOptions(screen.getByLabelText('Filter by mood'), 'calm');
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          requestPath(input).includes('mood=calm')
        )
      ).toBe(true);
    });
    expect(await screen.findByRole('heading', { name: 'Morning Pages' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Afternoon' })).not.toBeInTheDocument();

    // Clear filters
    await user.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(await screen.findByRole('heading', { name: 'Afternoon' })).toBeInTheDocument();

    // Filter by tag: Weather
    await user.selectOptions(screen.getByLabelText('Filter by tag'), '2');
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          requestPath(input).includes('tag_ids=2')
        )
      ).toBe(true);
    });
    expect(await screen.findByRole('heading', { name: 'Afternoon' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Morning Pages' })).not.toBeInTheDocument();
  });
});
