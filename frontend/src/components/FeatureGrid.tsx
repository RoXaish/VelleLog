import React from 'react';

interface Feature {
  title: string;
  description: string;
  icon: React.ReactNode;
}

const FEATURES: Feature[] = [
  {
    title: 'Live group availability',
    description:
      "Know who's free right now before you even open the group chat.",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M3 12h4l2.5-6 4 12L16 12h5" />
      </svg>
    ),
  },
  {
    title: 'Recurring weekly schedules',
    description:
      'Set your usual rhythm once and let it repeat every week.',
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M17 2l4 4-4 4" />
        <path d="M3 11V9a4 4 0 0 1 4-4h14" />
        <path d="M7 22l-4-4 4-4" />
        <path d="M21 13v2a4 4 0 0 1-4 4H3" />
      </svg>
    ),
  },
  {
    title: 'Common free-time discovery',
    description:
      'Find the exact windows where your whole group overlaps.',
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="3" y="4" width="18" height="18" rx="2" />
        <path d="M16 2v4M8 2v4M3 10h18" />
        <path d="M9.5 16.5l2 2 3.5-3.5" />
      </svg>
    ),
  },
  {
    title: 'Private timetable visibility',
    description:
      'Friends see free or busy — never event names, people, or places.',
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="4" y="10" width="16" height="11" rx="2" />
        <path d="M8 10V7a4 4 0 0 1 8 0v3" />
        <path d="M12 15v2" />
      </svg>
    ),
  },
];

export const FeatureGrid: React.FC = () => {
  return (
    <section id="features" className="section features">
      <div className="container">
        <div className="section-head">
          <span
            className="eyebrow reveal"
            style={{ '--reveal-delay': '0ms' } as React.CSSProperties}
          >
            Features
          </span>
          <h2
            className="section-title reveal"
            style={{ '--reveal-delay': '80ms' } as React.CSSProperties}
          >
            Built for real plans, not group-chat noise.
          </h2>
          <p
            className="section-sub reveal"
            style={{ '--reveal-delay': '160ms' } as React.CSSProperties}
          >
            Everything you need to coordinate with your people — without
            exposing your calendar.
          </p>
        </div>

        <div className="features-grid">
          {FEATURES.map((feature, index) => (
            <article
              key={feature.title}
              className="feature reveal"
              style={{ '--reveal-delay': `${220 + index * 90}ms` } as React.CSSProperties}
            >
              <span className="feature__icon">{feature.icon}</span>
              <h3 className="feature__title">{feature.title}</h3>
              <p className="feature__text">{feature.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};
