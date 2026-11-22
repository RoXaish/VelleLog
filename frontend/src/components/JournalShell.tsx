import React from 'react';
import { Link, NavLink } from 'react-router-dom';
import { BrandMark } from './BrandMark';

interface JournalShellProps {
  children: React.ReactNode;
  actions?: React.ReactNode;
}

export const JournalShell: React.FC<JournalShellProps> = ({
  children,
  actions,
}) => {
  return (
    <div className="journal-page">
      <a className="skip-to-content" href="#journal-main">
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

      <div className="journal-shell">
        <header className="journal-topbar">
          <Link to="/" className="nav-brand" aria-label="Velle Log home">
            <span className="nav-brand__mark">
              <BrandMark />
            </span>
            <span className="nav-brand__word">Velle Log</span>
          </Link>

          <nav className="journal-nav" aria-label="Journal navigation">
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `journal-nav__link${isActive ? ' is-active' : ''}`
              }
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/journal"
              end
              className={({ isActive }) =>
                `journal-nav__link${isActive ? ' is-active' : ''}`
              }
            >
              Journal
            </NavLink>
            <NavLink
              to="/tags"
              className={({ isActive }) =>
                `journal-nav__link${isActive ? ' is-active' : ''}`
              }
            >
              Tags
            </NavLink>
            <NavLink
              to="/account"
              className={({ isActive }) =>
                `journal-nav__link${isActive ? ' is-active' : ''}`
              }
            >
              Account
            </NavLink>
            {actions}
          </nav>
        </header>

        <main id="journal-main" className="journal-main">
          {children}
        </main>

        <footer className="journal-footnote">
          Private by design · Velle Log
        </footer>
      </div>
    </div>
  );
};
