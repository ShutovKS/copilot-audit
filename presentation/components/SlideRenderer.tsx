import React from 'react';
import { SlideData, SlideType } from '../types';
import CodeBlock from './CodeBlock';
import { 
  User, GitBranch, Search, Code, CheckCircle, Play, Ghost, EyeOff, 
  ZapOff, ShieldAlert, ArrowUp, Github, Server, Database, Atom,
  Cpu, FileJson, Layers, Bug, Workflow, Activity
} from 'lucide-react';

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
          case 'server': return <Server className={className} />;
          case 'database': return <Database className={className} />;
          case 'react': return <Atom className={className} />;
          // New Icons for Updated Features
          case 'cpu': return <Cpu className={className} />;
          case 'file-json': return <FileJson className={className} />;
          case 'layers': return <Layers className={className} />;
          case 'bug': return <Bug className={className} />;
          case 'workflow': return <Workflow className={className} />;
          
          default: return <User className={className} />;
      }
  };

  const renderBoldText = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, lineIndex) => (
      <p key={lineIndex} className="mb-2">
        {line.split(/(\*\*.*?\*\*)/).filter(part => part).map((part, partIndex) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={partIndex} className="font-bold text-[#a3ff00]">{part.slice(2, -2)}</strong>;
          }
          return <span key={partIndex}>{part}</span>;
        })}
      </p>
    ));
  };

  switch (slide.type) {
    case SlideType.TITLE:
      return (
        <div className="h-full flex items-center justify-between px-10">
          <div className="flex flex-col gap-6 max-w-2xl z-10">
            {/* Added whitespace-pre-line to handle newlines */}
            <h1 className="text-7xl font-bold text-white tracking-tight whitespace-pre-line leading-tight">{slide.title}</h1>
            <div className="mt-8 flex flex-col gap-2">
               <div className="text-2xl text-gray-300 font-light">Автономная Agentic-система генерации тестов</div>
               <div className="flex gap-3 mt-4">
                  {Array.isArray(slide.subtitle) ? (
                    slide.subtitle.map((name, index) => (
                      <div key={index} className="bg-[#1f2126] border border-[#333] px-4 py-2 rounded text-gray-300 text-sm font-mono">
                        {name}
                      </div>
                    ))
                  ) : null}
               </div>
            </div>
          </div>
          {/* Decorative Burst Background */}
          <div className="absolute bottom-0 right-0 w-1/2 h-full opacity-30 pointer-events-none overflow-hidden">
             <div className="w-[800px] h-[800px] bg-[#a3ff00] rounded-full absolute -bottom-40 -right-20 blur-3xl opacity-20"></div>
          </div>
           {/* Speaker Image Placeholder */}
           <div 
            className="relative z-10 w-1/2 h-2/3 flex items-end justify-center group"
            style={{ transform: 'translateX(8%)' }}
           >
              {Array.isArray(slide.image) ? (
                slide.image.map((img, index) => (
                  <div 
                    key={index}
                    className="absolute w-64 h-80 bg-gray-800 rounded-lg border-2 border-[#a3ff00] overflow-hidden shadow-[10px_10px_0px_0px_rgba(163,255,0,0.5)] transition-transform duration-300 ease-in-out hover:scale-110 hover:z-20"
                    style={{
                      transform: `rotate(${(index - 1) * 12}deg) translate(${(index - 1) * 65}%, 0)`,
                      zIndex: slide.image.length - index,
                    }}
                  >
                    <img 
                      src={img} 
                      alt={`Speaker ${index + 1}`}
                      className="w-full h-full object-cover grayscale hover:grayscale-0 transition-all duration-500" 
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = 'https://picsum.photos/seed/tech/400/600'; 
                      }}
                    />
                  </div>
                ))
              ) : null}
           </div>
        </div>
      );

    case SlideType.GRID_CARDS:
      return (
        <div className="h-full flex flex-col pt-4"> 
          <div className="grid grid-cols-4 gap-6 h-full pb-10 mt-4">
            {slide.content.map((card: any, idx: number) => (
              <div key={idx} className="bg-[#1f2126] p-6 flex flex-col gap-4 border border-[#333] hover:border-[#a3ff00] hover:translate-y-[-5px] transition-all duration-300 shadow-xl relative overflow-hidden group rounded-xl">
                <div className="absolute top-0 right-0 p-4 opacity-20 group-hover:opacity-100 transition-opacity">
                    {card.icon && renderIcon(card.icon, "w-10 h-10 text-[#a3ff00]")}
                </div>
                <h3 className="text-white text-xl font-bold mt-4 group-hover:text-[#a3ff00] transition-colors">{card.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{card.description}</p>
              </div>
            ))}
          </div>
        </div>
      );

    case SlideType.FLOWCHART:
      return (
        <div className="h-full flex flex-col justify-center pt-4">
          <div className="flex items-start justify-between gap-2 px-4">
             {slide.content.map((step: any, idx: number) => (
                 <React.Fragment key={idx}>
                    <div className="flex flex-col items-center gap-4 w-40 group relative">
                        <div className="w-20 h-20 bg-[#1f2126] rounded-2xl flex items-center justify-center border border-[#333] group-hover:border-[#a3ff00] group-hover:shadow-[0_0_20px_rgba(163,255,0,0.2)] transition-all z-10">
                            {renderIcon(step.icon)}
                        </div>
                        <div className="text-center">
                            <h4 className="text-white font-bold text-lg mb-1">{step.role}</h4>
                            <p className="text-xs text-gray-500 leading-snug">{step.description}</p> 
                        </div>
                    </div>
                    {idx < slide.content.length - 1 && (
                        <div className="h-20 flex items-center justify-center flex-1 relative">
                             <div className="absolute h-[2px] w-full bg-[#333] top-10"></div>
                             {idx === 2 && ( // Special visual for Batch split
                               <div className="absolute top-10 w-2 h-2 bg-[#a3ff00] rounded-full animate-ping"></div>
                             )}
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
          <div className="flex gap-8 h-full pb-4 items-stretch mt-4">
            <div className="flex-[1.2] overflow-hidden h-full">
                <CodeBlock code={slide.code || ''} className="h-full border-[#333]" fit={true} />
            </div>
            <div className="flex-1 flex flex-col justify-center pr-8">
                <div className="text-lg leading-relaxed text-gray-300">
                  {renderBoldText(slide.content)}
                </div>
            </div>
          </div>
        </div>
      );
    
    case SlideType.TERMINAL:
      return (
         <div className="h-full flex flex-col pt-4">
            <div className="flex-1 bg-[#131418] rounded-xl p-0 border border-[#333] font-mono text-xs overflow-hidden text-gray-300 relative shadow-2xl mt-4">
                 <div className="h-8 bg-[#1f2126] border-b border-[#333] flex items-center px-4 gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500"></div>
                    <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500"></div>
                    <span className="ml-4 text-[10px] text-gray-500">testops-forge — zsh</span>
                 </div>
                 <div className="p-6 overflow-auto h-[calc(100%-2rem)]">
                     {slide.code?.split('\n').map((line: string, i: number) => (
                         <div key={i} className={`mb-1 ${
                           line.startsWith('>') ? 'text-[#a3ff00]' : 
                           line.includes('ERROR') || line.includes('Fail') ? 'text-red-400' : 
                           line.includes('SUCCESS') ? 'text-emerald-400' :
                           line.startsWith('#') ? 'text-gray-500 italic' :
                           'text-gray-300'
                         }`}>
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
          <div className="flex-1 relative bg-[#131418] rounded-xl border border-[#333] shadow-2xl overflow-hidden flex flex-col w-10/12 mx-auto">
            <div className="absolute inset-0 flex items-center justify-center bg-[#1f2126]">
              <img src={slide.image} alt={slide.title} className="max-w-full max-h-full object-contain object-center border border-[#333]" />
            </div>

                 {slide.content.map((item: any, idx: number) => (
                    <div key={idx} 
                         className={`absolute flex flex-col items-center gap-2 z-10 transition-all hover:scale-110 cursor-pointer
                            ${item.position === 'left' ? 'left-[10%] top-1/2' : ''}
                            ${item.position === 'center' ? 'left-1/2 top-[40%] -translate-x-1/2' : ''}
                            ${item.position === 'right' ? 'right-[2%] top-[20%]' : ''}
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
            <div className="h-full flex flex-col pt-10 px-10 items-center text-center">
                 <h2 className="text-6xl font-bold mb-12 text-white"><span className="text-[#a3ff00]">TestOps</span> Evolution Forge</h2>
                 
                 <div className="grid grid-cols-3 gap-8 w-full max-w-5xl">
                     <div className="bg-[#1f2126] p-8 rounded-2xl border border-[#333] flex flex-col items-center">
                        <CheckCircle className="w-12 h-12 text-[#a3ff00] mb-4" />
                        <h3 className="text-xl font-bold mb-2">Production Ready</h3>
                        <p className="text-gray-400 text-sm">Full Cycle: От промпта до Merge Request</p>
                     </div>
                     <div className="bg-[#1f2126] p-8 rounded-2xl border border-[#333] flex flex-col items-center">
                        <ShieldAlert className="w-12 h-12 text-[#a3ff00] mb-4" />
                        <h3 className="text-xl font-bold mb-2">Self-Healing</h3>
                        <p className="text-gray-400 text-sm">Trace Inspector + Debug Agent</p>
                     </div>
                     <div className="bg-[#1f2126] p-8 rounded-2xl border border-[#333] flex flex-col items-center">
                        <Server className="w-12 h-12 text-[#a3ff00] mb-4" />
                        <h3 className="text-xl font-bold mb-2">Powered by Evolution</h3>
                        <p className="text-gray-400 text-sm">Qwen 2.5 Coder on Cloud.ru Infra</p>
                     </div>
                 </div>

                 <div className="mt-20 flex items-center gap-4 bg-[#2a2a2a] px-8 py-4 rounded-full border border-[#444]">
                     <Github className="w-6 h-6 text-white" />
                     <span className="text-gray-300 font-mono">github.com/ShutovKS/copilot-audit</span>
                 </div>
            </div>
        );

    default:
      return <div>Unknown Slide Type</div>;
  }
};

export default SlideRenderer;