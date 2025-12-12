import React from 'react';
import { SlideData, SlideType } from '../types';
import CodeBlock from './CodeBlock';
import { User, GitBranch, Search, Code, CheckCircle, Play, Ghost, EyeOff, ZapOff, ShieldAlert, ArrowUp, Github } from 'lucide-react';

interface SlideRendererProps {
  slide: SlideData;
}

const SlideRenderer: React.FC<SlideRendererProps> = ({ slide }) => {
  
  const renderIcon = (iconName: string, className: string = "w-8 h-8 text-[#a3ff00]") => {
      switch(iconName) {
          // Flowchart icons
          case 'user': return <User className={className} />;
          case 'git-branch': return <GitBranch className={className} />;
          case 'search': return <Search className={className} />;
          case 'code': return <Code className={className} />;
          case 'check-circle': return <CheckCircle className={className} />;
          case 'play': return <Play className={className} />;
          // Card icons
          case 'ghost': return <Ghost className={className} />;
          case 'eye-off': return <EyeOff className={className} />;
          case 'zap-off': return <ZapOff className={className} />;
          case 'shield-alert': return <ShieldAlert className={className} />;
          default: return <User className={className} />;
      }
  };

  switch (slide.type) {
    case SlideType.TITLE:
      return (
        <div className="h-full flex items-center justify-between px-10">
          <div className="flex flex-col gap-6 max-w-2xl z-10">
            <h1 className="text-7xl font-bold text-white tracking-tight">{slide.title}</h1>
            <div className="mt-12 bg-[#a3ff00] text-black p-4 inline-block transform -rotate-1 w-fit">
              <pre className="font-sans font-bold text-xl leading-tight whitespace-pre-wrap">
                {slide.subtitle}
              </pre>
            </div>
          </div>
          {/* Decorative Burst Background */}
          <div className="absolute bottom-0 right-0 w-1/2 h-full opacity-30 pointer-events-none overflow-hidden">
             <div className="w-[800px] h-[800px] bg-[#a3ff00] rounded-full absolute -bottom-40 -right-20 blur-3xl opacity-20"></div>
          </div>
           {/* Speaker Image Placeholder */}
           <div className="relative z-10 w-1/3 h-2/3 flex items-end justify-center">
              <div className="w-64 h-80 bg-gray-800 rounded-lg border-2 border-[#a3ff00] overflow-hidden shadow-[10px_10px_0px_0px_rgba(163,255,0,0.5)]">
                  <img 
                    src={slide.image} 
                    alt="Speaker" 
                    className="w-full h-full object-cover grayscale hover:grayscale-0 transition-all duration-500" 
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'https://picsum.photos/seed/speaker/400/600'; // Fallback
                    }}
                  />
              </div>
           </div>
        </div>
      );

    case SlideType.GRID_CARDS:
      return (
        <div className="h-full flex flex-col pt-4"> 
          {/* Title moved to header */}
          <div className="grid grid-cols-4 gap-6 h-full pb-10 mt-4">
            {slide.content.map((card: any, idx: number) => (
              <div key={idx} className="bg-[#2a2a2a] p-6 flex flex-col gap-4 border-t-4 border-[#a3ff00] hover:translate-y-[-5px] transition-transform duration-300 shadow-lg relative overflow-hidden group">
                <div className="absolute top-2 right-2 opacity-20 group-hover:opacity-100 transition-opacity">
                    {card.icon && renderIcon(card.icon, "w-12 h-12 text-[#a3ff00]")}
                </div>
                <h3 className="text-[#2ecc71] text-xl font-bold mt-4">{card.title}</h3>
                <p className="text-gray-300 text-lg leading-relaxed">{card.description}</p>
              </div>
            ))}
          </div>
        </div>
      );

    case SlideType.FLOWCHART:
      return (
        <div className="h-full flex flex-col justify-center pt-4">
          {/* Title moved to header */}
          <div className="flex items-start justify-between gap-2 px-4">
             {slide.content.map((step: any, idx: number) => (
                 <React.Fragment key={idx}>
                    <div className="flex flex-col items-center gap-4 w-40 group">
                        <div className="w-20 h-20 bg-[#2a2a2a] rounded-xl flex items-center justify-center border-2 border-transparent group-hover:border-[#a3ff00] transition-colors shadow-lg">
                            {renderIcon(step.icon)}
                        </div>
                        <div className="text-center">
                            <h4 className="text-[#2ecc71] font-bold text-lg mb-1">{step.role}</h4>
                            <p className="text-sm text-gray-300 leading-snug font-medium">{step.description}</p> 
                        </div>
                    </div>
                    {idx < slide.content.length - 1 && (
                        <div className="h-20 flex items-center justify-center flex-1">
                             <div className="h-[2px] w-full bg-gray-600 relative">
                                <div className="absolute right-0 -top-[3px] w-2 h-2 border-t-2 border-r-2 border-gray-600 rotate-45"></div>
                             </div>
                        </div>
                    )}
                 </React.Fragment>
             ))}
          </div>
        </div>
      );

    case SlideType.CODE_SPLIT:
      return (
        <div className="h-full flex flex-col pt-4">
          {/* Title moved to header */}
          <div className="flex gap-10 h-full pb-4 items-stretch mt-4">
            <div className="flex-1 overflow-hidden h-full">
                <CodeBlock code={slide.code || ''} className="h-full" fit={true} />
            </div>
            <div className="flex-1 flex flex-col justify-center">
                <div className="text-xl leading-8 text-gray-200 whitespace-pre-wrap">
                    {slide.content}
                </div>
            </div>
          </div>
        </div>
      );
    
    case SlideType.TERMINAL:
      return (
         <div className="h-full flex flex-col pt-4">
            {/* Title moved to header */}
            <div className="flex-1 bg-black rounded p-2 border border-gray-700 font-mono text-sm overflow-auto text-gray-300 relative shadow-2xl mt-4">
                 <div className="absolute top-0 left-0 right-0 h-6 bg-[#333] flex items-center px-2">
                    <span className="text-[10px] text-gray-400">bash — 80x24</span>
                 </div>
                 <div className="mt-8 px-4 pb-4 whitespace-pre-wrap">
                     {slide.code?.split('\n').map((line: string, i: number) => (
                         <div key={i} className={`${line.startsWith('$') ? 'text-white font-bold' : line.startsWith('#') ? 'text-[#a3ff00]' : line.includes("can't find") ? 'text-red-400' : 'text-gray-400'}`}>
                            {line}
                         </div>
                     ))}
                 </div>
            </div>
         </div>
      );

    case SlideType.UI_SCREENSHOT:
      return (
        <div className="h-full flex flex-col pt-4">
            {/* Title moved to header */}
            <div className="flex-1 relative bg-gray-900 rounded-lg border border-gray-700 shadow-2xl overflow-hidden flex flex-col mt-4">
                 {/* Browser Toolbar Mockup */}
                 <div className="h-8 bg-[#2d2d2d] border-b border-black flex items-center px-4 gap-2">
                    <div className="flex gap-1">
                        <div className="w-3 h-3 rounded-full bg-red-500"></div>
                        <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                        <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    </div>
                    <div className="flex-1 bg-[#1c1c1c] h-6 rounded mx-4 flex items-center px-2 text-[10px] text-gray-500 font-mono">
                        cloud.ru/internal/validops/debug
                    </div>
                 </div>

                 {/* Main UI Area Mockup */}
                 <div className="flex-1 flex text-xs font-mono">
                    {/* Left Panel: Chat */}
                    <div className="w-1/4 border-r border-black p-2 bg-[#1e1e1e] flex flex-col gap-2">
                        <div className="bg-[#2a2a2a] p-2 rounded text-gray-300">Run audit on payment page</div>
                        <div className="bg-[#2ecc71]/20 p-2 rounded text-[#2ecc71] self-end">Starting agent...</div>
                        <div className="bg-[#2a2a2a] p-2 rounded text-gray-300">Found 2 errors in DOM</div>
                    </div>
                    
                    {/* Center Panel: Editor */}
                    <div className="flex-1 bg-[#1e1e1e] p-2 text-gray-400">
                        <span className="text-[#ff7b72]">def</span> <span className="text-[#d2a8ff]">test_login</span>():<br/>
                        &nbsp;&nbsp;page.goto(<span className="text-[#a5d6ff]">'/login'</span>)<br/>
                        &nbsp;&nbsp;<span className="text-gray-500"># Fix: Wait for hydration</span><br/>
                        &nbsp;&nbsp;page.wait_for_selector(<span className="text-[#a5d6ff]">'#submit'</span>)
                    </div>

                    {/* Right Panel: Logs */}
                    <div className="w-1/4 border-l border-black bg-[#111] p-2 text-[10px] font-mono text-gray-500">
                        <div className="text-green-500">[INFO] Router connected</div>
                        <div className="text-blue-500">[DEBUG] Parsing AST...</div>
                        <div className="text-yellow-500">[WARN] Deprecated API</div>
                    </div>
                 </div>

                 {/* Overlays / Arrows */}
                 {slide.content.map((item: any, idx: number) => (
                    <div key={idx} 
                         className={`absolute flex flex-col items-center gap-2 z-10 transition-all hover:scale-110
                            ${item.position === 'left' ? 'left-[10%] top-1/2' : ''}
                            ${item.position === 'center' ? 'left-1/2 top-[40%] -translate-x-1/2' : ''}
                            ${item.position === 'right' ? 'right-[10%] top-1/2' : ''}
                         `}>
                         <div className="bg-[#a3ff00] text-black font-bold px-3 py-1 rounded shadow-lg text-sm whitespace-nowrap">
                             {item.label}
                         </div>
                         <ArrowUp className="text-[#a3ff00] w-6 h-6 animate-bounce" />
                    </div>
                 ))}
            </div>
        </div>
      );

    case SlideType.OUTRO:
        return (
            <div className="h-full flex flex-col pt-2 px-10"> {/* Reduced pt-10 to pt-2 */}
                 <h2 className="text-6xl font-bold mb-8 text-[#a3ff00] border-b-4 border-white pb-4 w-fit">{slide.title}</h2> {/* Reduced mb-16 to mb-8 */}
                 
                 <div className="flex items-start justify-between gap-10">
                     <div className="w-1/2">
                        <ul className="space-y-8">
                            {Array.isArray(slide.content) && slide.content.map((item: string, idx: number) => (
                                <li key={idx} className="text-3xl text-white font-light flex items-start gap-4">
                                    <CheckCircle className="text-[#2ecc71] w-8 h-8 mt-1 shrink-0" />
                                    <span>{item}</span>
                                </li>
                            ))}
                        </ul>
                     </div>
                     
                     {/* Links Section */}
                     <div className="w-1/2 flex flex-col items-start justify-center p-8 bg-[#2a2a2a] rounded-xl border border-gray-700 shadow-2xl relative overflow-hidden group">
                         <div className="flex items-center gap-4 mb-4 z-10">
                             <Github className="w-12 h-12 text-white" />
                             <span className="text-gray-400 text-sm uppercase tracking-widest">Source Code</span>
                         </div>
                         
                         <a 
                           href={slide.subtitle} 
                           target="_blank" 
                           rel="noreferrer"
                           className="text-2xl md:text-3xl font-bold text-[#a3ff00] break-all hover:underline decoration-2 underline-offset-4 z-10 font-mono"
                         >
                            {slide.subtitle?.replace('https://', '')}
                         </a>
                         
                         {/* Background Accent for Link Card */}
                         <div className="absolute top-0 right-0 bg-white/5 w-32 h-32 rounded-full blur-2xl -mr-10 -mt-10 group-hover:bg-[#a3ff00]/20 transition-colors duration-500"></div>
                     </div>
                 </div>

                 <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-gradient-to-tl from-[#2ecc71] to-transparent opacity-10 blur-3xl rounded-full pointer-events-none"></div>
            </div>
        );

    default:
      return <div>Unknown Slide Type</div>;
  }
};

export default SlideRenderer;