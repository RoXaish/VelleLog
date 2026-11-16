import React from 'react';
import { Link } from 'react-router-dom';

export const Hero: React.FC = () => {
  return (
    <section id="top" className="hero">
      <div className="container">
        <span className="hero__eyebrow hero-anim" style={{ animationDelay: '0ms' }}>
          <span className="hero__eyebrow-dot" />
          Private availability coordination
        </span>

        <h1 className="hero__title hero-anim" style={{ animationDelay: '90ms' }}>
          Make time for the
          <br />
          <span className="grad-text">people who matter.</span>
        </h1>

        <p className="hero__subtitle hero-anim" style={{ animationDelay: '180ms' }}>
          See who's free, find the perfect time, and bring your group together —
          without endless messages.
        </p>

        <div className="hero__actions hero-anim" style={{ animationDelay: '270ms' }}>
          <Link to="/signup" className="btn btn--primary">
            <span>Get started</span>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M3.5 8H12.5"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
              />
              <path
                d="M8.5 4L12.5 8L8.5 12"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </Link>

          <a href="#how-it-works" className="btn btn--ghost">
            <span>See how it works</span>
          </a>
        </div>
      </div>
    </section>
  );
};
