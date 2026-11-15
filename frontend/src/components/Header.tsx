import React, { useEffect, useRef, useState } from 'react';

const NAV_LINKS = [
  { href: '#product', label: 'Product' },
  { href: '#how-it-works', label: 'How it works' },
  { href: '#features', label: 'Features' },
];

const BrandMark: React.FC = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <circle cx="16" cy="16" r="12.5" stroke="currentColor" strokeWidth="1.6" strokeOpacity="0.55" />
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

export const Header: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (!menuOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false);
    };

    const onPointerDown = (event: PointerEvent) => {
      if (navRef.current && !navRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    document.addEventListener('pointerdown', onPointerDown);

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('pointerdown', onPointerDown);
    };
  }, [menuOpen]);

  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="site-nav-wrap">
      <nav
        ref={navRef}
        className={`site-nav ${scrolled ? 'is-scrolled' : ''}`}
        aria-label="Primary navigation"
      >
        <a href="#top" className="nav-brand" aria-label="Velle Log home">
          <span className="nav-brand__mark">
            <BrandMark />
          </span>
          <span className="nav-brand__word">Velle Log</span>
        </a>

        <div className="nav-links">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href}>
              {link.label}
            </a>
          ))}
        </div>

        <div className="nav-actions">
          <button
            type="button"
            className="nav-login"
            disabled
            aria-label="Log in — not available in this preview build"
            title="Log in arrives in a later milestone"
          >
            Log in
          </button>

          <a href="#product" className="nav-cta">
            Get started
          </a>

          <button
            type="button"
            className="nav-toggle"
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path
                  d="M3.5 3.5L12.5 12.5M12.5 3.5L3.5 12.5"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path
                  d="M2.5 4.5H13.5M2.5 8H13.5M2.5 11.5H13.5"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                />
              </svg>
            )}
          </button>
        </div>

        {menuOpen && (
          <div id="mobile-menu" className="mobile-menu">
            {NAV_LINKS.map((link) => (
              <a key={link.href} href={link.href} onClick={closeMenu}>
                {link.label}
              </a>
            ))}
            <button type="button" className="mobile-menu__login" disabled>
              Log in
              <span className="mobile-menu__soon">Soon</span>
            </button>
          </div>
        )}
      </nav>
    </div>
  );
};
