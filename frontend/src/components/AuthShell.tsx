import React from 'react';
import { Link } from 'react-router-dom';
import { BrandMark } from './BrandMark';

interface AuthShellProps {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
}

export const AuthShell: React.FC<AuthShellProps> = ({
  eyebrow,
  title,
  description,
  children,
}) => {
  return (
    <div className="auth-page">
      <a className="skip-to-content" href="#auth-main">
        Skip to content
      </a>

      <div className="aurora" aria-hidden="true">
        <div className="aurora__streak aurora__streak--1" />
        <div className="aurora__streak aurora__streak--2" />
        <div className="aurora__streak aurora__streak--3" />
        <div className="aurora__streak aurora__streak--4" />
        <div className="aurora__glow aurora__glow--a" />
        <div className="aurora__glow aurora__glow--b" />
        <div className="aurora__glow aurora__glow--c" />
      </div>
      <div className="vignette" aria-hidden="true" />
      <div className="grain-overlay" aria-hidden="true" />

      <div className="auth-shell">
        <header className="auth-topbar">
          <Link to="/" className="nav-brand" aria-label="Velle Log home">
            <span className="nav-brand__mark">
              <BrandMark />
            </span>
            <span className="nav-brand__word">Velle Log</span>
          </Link>
          <Link to="/" className="auth-home-link">
            Back to home
          </Link>
        </header>

        <main id="auth-main" className="auth-main">
          <section className="auth-card">
            <span className="auth-eyebrow">{eyebrow}</span>
            <h1 className="auth-title">{title}</h1>
            <p className="auth-description">{description}</p>
            {children}
          </section>
        </main>

        <footer className="auth-footnote">
          Private by design · Velle Log
        </footer>
      </div>
    </div>
  );
};
