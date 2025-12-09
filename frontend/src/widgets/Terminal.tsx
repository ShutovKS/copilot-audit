import { Terminal as TerminalIcon, CheckCircle2, AlertCircle, Loader2, Activity, BrainCircuit, Code2, ShieldCheck, Sparkles, Zap, ChevronDown, ChevronRight, Settings } from 'lucide-react';
import { useAppStore } from '../entities/store';
import { useEffect, useRef, useState } from 'react';

// Pipeline Steps Definition
const STEPS = [
    { id: 'analyst', label: 'Анализ', icon: BrainCircuit },
    { id: 'coder', label: 'Кодинг', icon: Code2 },
    { id: 'reviewer', label: 'Проверка', icon: ShieldCheck },
];

const LogItem = ({ log, timestamp }: { log: string, timestamp: string }) => {
    const [expanded, setExpanded] = useState(false);
    // Reduced threshold to 60 chars so more logs are collapsible
    const isLong = log.length > 60 || log.includes('\n');
    
    return (
        <div className="flex gap-3 text-[11px] leading-relaxed animate-in fade-in slide-in-from-bottom-2 duration-300">
            <span className="text-zinc-600 shrink-0 select-none font-medium w-12 text-right">
                {timestamp}
            </span>
            <div className="flex-1 min-w-0">
                <div 
                    className={`break-words whitespace-pre-wrap ${ 
                        log.includes('Error') ? 'text-red-400' : 
                        log.includes('Success') ? 'text-emerald-400' : 
                        log.includes('System') ? 'text-blue-400' :
                        log.includes('Analyst') ? 'text-purple-400' :
                        log.includes('Coder') ? 'text-yellow-400' :
                        log.includes('Reviewer') ? 'text-cyan-400' :
                        'text-zinc-300'
                    } ${!expanded && isLong ? 'line-clamp-2' : ''}`}
                >
                    {log}
                </div>
                {isLong && (
                    <button 
                        onClick={() => setExpanded(!expanded)}
                        className="flex items-center gap-1 text-[9px] text-muted hover:text-white mt-1 transition-colors"
                    >
                        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                        {expanded ? 'Свернуть' : 'Показать полностью'}
                    </button>
                )}
            </div>
        </div>
    );
};

interface TerminalProps {
    onOpenSettings: () => void;
}

export const Terminal = ({ onOpenSettings }: TerminalProps) => {
  const { logs, status } = useAppStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Determine current active step based on logs
  const getCurrentStepIndex = () => {
      if (status === 'success') return STEPS.length; 
      if (status === 'error') return -1;
      
      const lastLog = logs[logs.length - 1] || '';
      if (lastLog.includes('Reviewer')) return 2;
      if (lastLog.includes('Coder')) return 1;
      if (lastLog.includes('Analyst')) return 0;
      return 0;
  };

  const activeStepIndex = getCurrentStepIndex();
  const isIdle = status === 'idle';

  return (
    <div className="flex flex-col gap-4 h-full">
        {/* Top Card: Status or Pipeline */}
        <div className="bg-[#1f2126] rounded-2xl p-6 shadow-xl border border-white/5 relative overflow-hidden">
            {/* Header with Settings */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-2">
                    <Activity size={16} className={status === 'processing' ? 'text-[#00b67a] animate-pulse' : 'text-muted'} />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                        {status === 'processing' ? 'Workflow Active' : status === 'success' ? 'Task Completed' : status === 'error' ? 'Task Failed' : 'Ready'}
                    </h3>
                </div>
                <div className="flex items-center gap-2">
                    {status === 'processing' && <Loader2 size={16} className="animate-spin text-[#00b67a]" />}
                    <button 
                        onClick={onOpenSettings}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-muted hover:text-white transition-colors"
                        title="Settings"
                    >
                        <Settings size={16} />
                    </button>
                </div>
            </div>

            {isIdle ? (
                <div className="flex flex-col items-center justify-center py-4 animate-in fade-in zoom-in duration-500">
                    <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#00b67a]/10 to-blue-500/10 flex items-center justify-center mb-4 shadow-[0_0_30px_rgba(0,182,122,0.1)] border border-white/5">
                        <Sparkles size={28} className="text-[#00b67a]" />
                    </div>
                    <p className="text-xs text-muted text-center max-w-[200px] leading-relaxed">
                        Система готова к работе.
                        <br/>Запустите генерацию слева.
                    </p>
                </div>
            ) : (
                <>
                    <div className="flex justify-between relative px-2 mb-2">
                        {/* Connecting Lines Background */}
                        <div className="absolute top-1/2 left-4 right-4 h-0.5 bg-white/5 -translate-y-1/2 z-0 rounded-full" />
                        
                        {/* Progress Line */}
                        <div 
                            className={`absolute top-1/2 left-4 h-0.5 -translate-y-1/2 z-0 transition-all duration-700 ease-in-out rounded-full ${status === 'error' ? 'bg-error' : 'bg-gradient-to-r from-[#00b67a] to-blue-500'}`}
                            style={{ width: `${Math.min((activeStepIndex / (STEPS.length - 1)) * 100, 100)}%` }}
                        />
                        
                        {STEPS.map((step, index) => {
                            const isActive = index === activeStepIndex && status === 'processing';
                            const isPast = index < activeStepIndex || status === 'success';
                            const isError = status === 'error' && index === activeStepIndex;
                            
                            return (
                                <div key={step.id} className="relative z-10 flex flex-col items-center gap-4">
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-500 border-2 shadow-lg
                                        ${isActive ? 'bg-[#1f2126] border-[#00b67a] text-[#00b67a] scale-110 shadow-[0_0_15px_rgba(0,182,122,0.3)]' : 
                                          isError ? 'bg-[#1f2126] border-error text-error shadow-error/20' :
                                          isPast ? 'bg-[#2b2d33] border-[#2b2d33] text-white shadow-md' : 
                                          'bg-[#18191d] border-white/5 text-muted'}
                                    `}>
                                        {isError ? <AlertCircle size={18} /> : isPast ? <CheckCircle2 size={18} strokeWidth={3} className="text-[#00b67a]" /> : <step.icon size={18} />}
                                    </div>
                                    
                                    {/* Label */}
                                    <div className={`absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap flex flex-col items-center transition-all duration-300`}>
                                        <span className={`text-[10px] font-bold uppercase tracking-wider ${isActive ? 'text-white' : isError ? 'text-error' : isPast ? 'text-zinc-400' : 'text-muted'}`}>
                                            {step.label}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    <div className="h-6" />
                </>
            )}
        </div>

        {/* Logs Card */}
        <div className="flex-1 bg-[#1f2126] rounded-2xl p-0 shadow-xl border border-white/5 flex flex-col overflow-hidden transition-all duration-300 hover:border-white/10">
             <div className="p-3 px-4 border-b border-white/5 flex justify-between items-center bg-[#18191d]/30">
                <div className="flex items-center gap-2">
                    <TerminalIcon size={14} className="text-muted" />
                    <h3 className="text-xs font-medium text-zinc-400">System Logs</h3>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${status === 'processing' ? 'bg-[#00b67a] animate-pulse' : status === 'error' ? 'bg-error' : 'bg-zinc-700'}`} />
                    <span className="text-[9px] text-muted uppercase tracking-wider">
                        {status === 'processing' ? 'Live' : status === 'error' ? 'Failed' : 'Offline'}
                    </span>
                </div>
             </div>
             <div className="flex-1 overflow-y-auto p-4 space-y-2.5 font-mono scrollbar-thin scrollbar-thumb-white/10">
                {logs.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-muted opacity-20 gap-2">
                        <Zap size={32} />
                        <div className="text-xs font-medium">Жду событий...</div>
                    </div>
                )}
                {logs.map((log, i) => (
                    <LogItem key={i} log={log} timestamp={new Date().toLocaleTimeString().split(' ')[0]} />
                ))}
                <div ref={bottomRef} />
             </div>
        </div>
    </div>
  );
};
