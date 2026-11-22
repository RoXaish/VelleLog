import React from 'react';
import type { Mood } from '../lib/api';
import { moodLabel } from '../lib/moods';

interface MoodBadgeProps {
  mood: Mood;
  compact?: boolean;
}

export const MoodBadge: React.FC<MoodBadgeProps> = ({ mood, compact }) => (
  <span
    className={`mood-badge mood-badge--${mood}${compact ? ' mood-badge--compact' : ''}`}
  >
    <span className="mood-badge__dot" aria-hidden="true" />
    {moodLabel(mood)}
  </span>
);
