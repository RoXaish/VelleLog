import React from 'react';

interface Step {
  title: string;
  description: string;
  icon: React.ReactNode;
}

const STEPS: Step[] = [
  {
    title: 'Create your group.',
    description:
      'Bring the people you actually spend time with into one private circle.',
    icon: (
      <svg
        width="19"
        height="19"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    title: 'Add your weekly schedule.',
    description:
      'Mark your recurring busy hours once. Event labels stay private.',
    icon: (
      <svg
        width="19"
        height="19"
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
        <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" />
      </svg>
    ),
  },
  {
    title: 'Find a time everyone is free.',
    description:
      'See the shared open windows at a glance and lock in the plan.',
    icon: (
      <svg
        width="19"
        height="19"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3.5 2" />
      </svg>
    ),
  },
];

export const HowItWorks: React.FC = () => {
  return (
    <section id="how-it-works" className="section how">
      <div className="container">
        <div className="section-head">
          <span
            className="eyebrow reveal"
            style={{ '--reveal-delay': '0ms' } as React.CSSProperties}
          >
            How it works
          </span>
          <h2
            className="section-title reveal"
            style={{ '--reveal-delay': '80ms' } as React.CSSProperties}
          >
            Three steps. One time that works.
          </h2>
          <p
            className="section-sub reveal"
            style={{ '--reveal-delay': '160ms' } as React.CSSProperties}
          >
            No polls, no endless back-and-forth. Just your group's rhythm, in
            one place.
          </p>
        </div>

        <ol className="steps">
          {STEPS.map((step, index) => (
            <li
              key={step.title}
              className="step reveal"
              style={{ '--reveal-delay': `${220 + index * 110}ms` } as React.CSSProperties}
            >
              <span className="step__index">{String(index + 1).padStart(2, '0')}</span>
              <span className="step__icon">{step.icon}</span>
              <h3 className="step__title">{step.title}</h3>
              <p className="step__text">{step.description}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
};
