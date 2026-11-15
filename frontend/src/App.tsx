import React, { useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { ProductPreview } from './components/ProductPreview';
import { HowItWorks } from './components/HowItWorks';
import { FeatureGrid } from './components/FeatureGrid';
import { Footer } from './components/Footer';
import './App.css';

const ScrollProgress: React.FC = () => {
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let frame = 0;

    const update = () => {
      const doc = document.documentElement;
      const max = doc.scrollHeight - doc.clientHeight;
      const progress = max > 0 ? Math.min(doc.scrollTop / max, 1) : 0;
      if (barRef.current) {
        barRef.current.style.transform = `scaleX(${progress})`;
      }
      frame = 0;
    };

    const onScroll = () => {
      if (!frame) {
        frame = window.requestAnimationFrame(update);
      }
    };

    update();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);

    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      if (frame) {
        window.cancelAnimationFrame(frame);
      }
    };
  }, []);

  return <div className="scroll-progress" ref={barRef} aria-hidden="true" />;
};

export const App: React.FC = () => {
  useEffect(() => {
    const elements = Array.from(document.querySelectorAll<HTMLElement>('.reveal'));
    if (elements.length === 0) return;

    if (!('IntersectionObserver' in window)) {
      elements.forEach((el) => el.classList.add('is-visible'));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -6% 0px' }
    );

    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="app-container">
      <a className="skip-to-content" href="#main-content">
        Skip to content
      </a>

      <ScrollProgress />

      {/* Cinematic atmosphere */}
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

      <Header />

      <main id="main-content">
        <Hero />
        <ProductPreview />
        <HowItWorks />
        <FeatureGrid />
      </main>

      <Footer />
    </div>
  );
};

export default App;
