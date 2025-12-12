import React from 'react';

interface CodeBlockProps {
  code: string;
  className?: string;
  fit?: boolean;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ code, className = "", fit = false }) => {
  return (
    <div className={`bg-[#2b2b2b] p-4 md:p-6 rounded-lg border border-gray-700 shadow-xl flex flex-col ${fit ? 'overflow-hidden h-full' : 'overflow-hidden'} ${className}`}>
      {/* Mac-style dots for decoration */}
      <div className="flex gap-2 mb-3 shrink-0">
        <div className="w-3 h-3 rounded-full bg-red-500"></div>
        <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
        <div className="w-3 h-3 rounded-full bg-green-500"></div>
      </div>
      
      {/* Increased font size from text-[10px] to text-xs (12px) and adjusted leading */}
      <pre className={`font-mono leading-snug text-gray-300 ${fit ? 'text-base whitespace-pre-wrap overflow-hidden h-full' : 'text-sm md:text-base overflow-x-auto'}`}>
        <code>{code.split('\n').map((line, i) => (
          <div key={i} className={fit ? "min-h-[1.1em]" : "min-h-[1.5em]"}>
            {/* Simple syntax simulation based on keywords */}
            {line.split(/(\s+)/).map((part, j) => {
               if (['def', 'class', 'import', 'from', 'return', 'if', 'else', 'for', 'async', 'await', 'while'].includes(part)) return <span key={j} className="text-[#ff7b72]">{part}</span>;
               if (['self', 'True', 'False', 'None'].includes(part)) return <span key={j} className="text-[#79c0ff]">{part}</span>;
               if (part.startsWith('"') || part.startsWith("'") || part.endsWith('"') || part.endsWith("'")) return <span key={j} className="text-[#a5d6ff]">{part}</span>;
               if (part.includes('(') || part.includes(')')) return <span key={j} className="text-[#d2a8ff]">{part}</span>;
               // Comments
               if (part.trim().startsWith('#')) return <span key={j} className="text-gray-500">{part}</span>;
               return <span key={j}>{part}</span>;
            })}
          </div>
        ))}</code>
      </pre>
    </div>
  );
};

export default CodeBlock;