import type { Mood } from './api';

export const MOOD_LABELS: Record<Mood, string> = {
  happy: 'Happy',
  calm: 'Calm',
  excited: 'Excited',
  grateful: 'Grateful',
  neutral: 'Neutral',
  sad: 'Sad',
  anxious: 'Anxious',
  stressed: 'Stressed',
};

export const MOOD_OPTIONS = (Object.keys(MOOD_LABELS) as Mood[]).map(
  (value) => ({ value, label: MOOD_LABELS[value] })
);

export function moodLabel(mood: Mood): string {
  return MOOD_LABELS[mood];
}
