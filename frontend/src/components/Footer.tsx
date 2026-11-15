import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer__inner">
          <div className="footer__brand">
            <div className="footer__brand-row">
              <span className="footer__mark" aria-hidden="true">
                <svg width="15" height="15" viewBox="0 0 32 32" fill="none">
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
              </span>
              Velle Log
            </div>
            <p className="footer__tagline">Make time for the people who matter.</p>
          </div>

          <nav className="footer__links" aria-label="Footer navigation">
            <a href="#product">Product</a>
            <a href="#how-it-works">How it works</a>
            <a href="#features">Features</a>
          </nav>

          <div className="footer__legal">
            <span>© 2026 Velle Log. All rights reserved.</span>
            <span>Preview build — availability data is illustrative.</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
