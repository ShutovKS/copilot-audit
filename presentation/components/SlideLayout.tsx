import React from 'react';
import { Box, ChevronLeft, ChevronRight } from 'lucide-react';
import { SlideType } from '../types';

interface SlideLayoutProps {
  children: React.ReactNode;
  slideNumber: number;
  totalSlides: number;
  onPrev: () => void;
  onNext: () => void;
  title?: string;
  type?: SlideType;
}

const SlideLayout: React.FC<SlideLayoutProps> = ({ children, slideNumber, totalSlides, onPrev, onNext, title, type }) => {
  
  const showHeaderTitle = type !== SlideType.TITLE && type !== SlideType.OUTRO;

  return (
    <div className="relative w-full h-full bg-[#1c1c1c] overflow-hidden flex flex-col font-sans text-white border-8 border-[#1c1c1c]">
      
      {/* Top Header Bar - Dark Theme */}
      <div className="absolute top-0 left-0 right-0 h-16 bg-[#141414] border-b border-[#333] flex items-center justify-between px-8 z-20">
         
         {/* Left Side: Slide Title (conditionally rendered) */}
         <div className="flex items-center">
            {showHeaderTitle && (
              <h2 className="text-white font-bold text-2xl tracking-tight uppercase border-l-4 border-[#a3ff00] pl-4">
                {title}
              </h2>
            )}
         </div>

         {/* Right Side: Fake Logo Area */}
         <div className="flex items-center gap-2">
            <div className="h-8 w-8 bg-[#2ecc71] flex items-center justify-center rounded">
              <Box className="text-white w-6 h-6" />
            </div>
            <span className="text-white font-bold text-xl tracking-tight">cloud.ru</span>
         </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 mt-16 px-12 py-8 relative z-0 mb-8">
        {/* Crop Marks (Decorative corners) - Adjusted positions to avoid overlap */}
        <div className="absolute top-4 left-4 w-4 h-4 border-l-2 border-t-2 border-white opacity-30"></div>
        <div className="absolute top-4 right-4 w-4 h-4 border-r-2 border-t-2 border-white opacity-30"></div>
        <div className="absolute bottom-4 left-4 w-4 h-4 border-l-2 border-b-2 border-white opacity-30"></div>
        <div className="absolute bottom-4 right-4 w-4 h-4 border-r-2 border-b-2 border-white opacity-30"></div>

        {children}
      </div>

      {/* Footer - Contains Copyright and Navigation */}
      <div className="absolute bottom-0 left-0 w-full px-8 py-2 bg-[#1c1c1c] flex items-center justify-between border-t border-[#333] z-30">
        <div className="text-[10px] text-gray-500 font-mono">
          ©2025 Cloud.ru Любое копирование и воспроизведение содержания без разрешения правообладателя запрещено.
        </div>

        {/* Navigation Controls */}
        <div className="flex items-center gap-3">
           <button 
             onClick={onPrev}
             disabled={slideNumber === 1}
             className="p-1 hover:bg-gray-800 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
             aria-label="Previous slide"
           >
             <ChevronLeft size={16} />
           </button>
           
           <span className="text-gray-400 font-mono text-xs">
             {slideNumber} / {totalSlides}
           </span>

           <button 
             onClick={onNext}
             disabled={slideNumber === totalSlides}
             className="p-1 hover:bg-gray-800 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
             aria-label="Next slide"
           >
             <ChevronRight size={16} />
           </button>
        </div>
      </div>
    </div>
  );
};

export default SlideLayout;