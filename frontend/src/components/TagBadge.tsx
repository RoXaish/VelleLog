import React from 'react';

interface TagBadgeProps {
  name: string;
}

export const TagBadge: React.FC<TagBadgeProps> = ({ name }) => (
  <span className="tag-badge">{name}</span>
);
