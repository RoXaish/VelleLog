import React from 'react';

export const BrandMark: React.FC<{ size?: number }> = ({ size = 18 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <circle
      cx="16"
      cy="16"
      r="12.5"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeOpacity="0.55"
    />
    <path
      d="M16 8.5V16L20.5 20.5"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <circle cx="16" cy="16" r="2.2" fill="currentColor" />
  </svg>
);
