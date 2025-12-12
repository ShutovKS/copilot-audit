import React, { useState, useEffect } from 'react';
import SlideLayout from './components/SlideLayout';
import SlideRenderer from './components/SlideRenderer';
import { SLIDES } from './constants';

const App: React.FC = () => {
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);

  const totalSlides = SLIDES.length;
  const currentSlide = SLIDES[currentSlideIndex];

  const nextSlide = () => {
    if (currentSlideIndex < totalSlides - 1) {
      setCurrentSlideIndex(prev => prev + 1);
    }
  };

  const prevSlide = () => {
    if (currentSlideIndex > 0) {
      setCurrentSlideIndex(prev => prev - 1);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Enter') {
        nextSlide();
      } else if (e.key === 'ArrowLeft') {
        prevSlide();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentSlideIndex]);

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-2 md:p-8">
      
      {/* Slide Container - Aspect Ratio 16:9 */}
      <div className="relative w-full max-w-7xl aspect-video shadow-2xl">
        <SlideLayout 
          slideNumber={currentSlideIndex + 1}
          totalSlides={totalSlides}
          onPrev={prevSlide}
          onNext={nextSlide}
          title={currentSlide.title}
          type={currentSlide.type}
        >
          <SlideRenderer slide={currentSlide} />
        </SlideLayout>
      </div>
      
    </div>
  );
};

export default App;