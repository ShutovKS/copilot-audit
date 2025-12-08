import { Terminal as TerminalIcon, CheckCircle2, Loader2, Activity, BrainCircuit, Code2, ShieldCheck, Sparkles, Zap } from 'lucide-react';
import { useAppStore } from '../entities/store';
import { useEffect, useRef } from 'react';

// Pipeline Steps Definition
const STEPS = [
    { id: 'analyst', label: 'Анализ', icon: BrainCircuit },
    { id: 'coder', label: 'Кодинг', icon: Code2 },
    { id: 'reviewer', label: 'Проверка', icon: ShieldCheck },
];

export const Terminal = () => {
  const { logs, status } = useAppStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Determine current active step based on logs
  const getCurrentStepIndex = () => {
      if (status === 'success') return STEPS.length; // All done
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
        <div className="bg-[#1f2126] rounded-2xl p-5 shadow-xl border border-white/5 relative overflow-hidden">
            {isIdle ? (
                // Idle State UI
                <div className="flex flex-col items-center justify-center py-2 animate-in fade-in zoom-in duration-500">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center mb-3 shadow-[0_0_20px_rgba(0,182,122,0.2)]">
                        <Sparkles size={24} className="text-primary animate-pulse" />
                    </div>
                    <h3 className="text-sm font-bold text-white mb-1">AI Agent Ready</h3>
                    <p className="text-[10px] text-muted text-center max-w-[200px]">
                        Готов к генерации тестов. Введите требования слева.
                    </p>
                </div>
            ) : (
                // Active Pipeline UI
                <>
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <Activity size={14} className={status === 'processing' ? 'text-primary animate-pulse' : 'text-muted'} />
                            <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
                                {status === 'success' ? 'Task Completed' : 'Workflow Active'}
                            </h3>
                        </div>
                        {status === 'processing' && <Loader2 size={14} className="animate-spin text-primary" />}
                    </div>
                    
                    <div className="flex justify-between relative px-2">
                        {/* Connecting Lines Background */}
                        <div className="absolute top-1/2 left-2 right-2 h-0.5 bg-white/5 -translate-y-1/2 z-0 rounded-full" />
                        
                        {/* Progress Line */}
                        <div 
                            className="absolute top-1/2 left-2 h-0.5 bg-gradient-to-r from-primary to-secondary -translate-y-1/2 z-0 transition-all duration-700 ease-in-out rounded-full"
                            style={{ width: `${Math.min((activeStepIndex / (STEPS.length - 1)) * 100, 100)}%` }}
                        />
                        
                        {STEPS.map((step, index) => {
                            const isActive = index === activeStepIndex && status === 'processing';
                            const isPast = index < activeStepIndex || status === 'success';
                            
                            return (
                                <div key={step.id} className="relative z-10 flex flex-col items-center gap-3">
                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-500 border-2
                                        ${isActive ? 'bg-[#1f2126] border-primary text-primary scale-110 shadow-[0_0_15px_rgba(0,182,122,0.5)]' : 
                                          isPast ? 'bg-primary border-primary text-[#131418]' : 
                                          'bg-[#18191d] border-white/5 text-muted'}
                                    `}>
                                        {isPast ? <CheckCircle2 size={14} strokeWidth={3} /> : <step.icon size={14} />}
                                    </div>
                                    
                                    {/* Label with Glow for active */}
                                    <div className={`absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap flex flex-col items-center transition-all duration-300 ${isActive ? 'translate-y-0 opacity-100' : 'translate-y-1 opacity-70'}`}>
                                        <span className={`text-[10px] font-bold ${isActive ? 'text-white' : 'text-muted'}`}>
                                            {step.label}
                                        </span>
                                        {isActive && (
                                            <span className="text-[8px] text-primary animate-pulse">Processing...</span>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    <div className="h-4" /> {/* Spacer for labels */}
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
                    <div className={`w-1.5 h-1.5 rounded-full ${status === 'processing' ? 'bg-primary animate-pulse' : 'bg-zinc-700'}`} />
                    <span className="text-[9px] text-muted uppercase tracking-wider">
                        {status === 'processing' ? 'Live' : 'Offline'}
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
                    <div key={i} className="flex gap-3 text-[11px] leading-relaxed animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <span className="text-zinc-600 shrink-0 select-none font-medium w-12 text-right">
                            {new Date().toLocaleTimeString().split(' ')[0]}
                        </span>
                        <div className="flex-1 min-w-0">
                            <span className={`break-words ${ 
                                log.includes('Error') ? 'text-red-400' : 
                                log.includes('Success') ? 'text-emerald-400' : 
                                log.includes('System') ? 'text-blue-400' :
                                log.includes('Analyst') ? 'text-purple-400' :
                                log.includes('Coder') ? 'text-yellow-400' :
                                log.includes('Reviewer') ? 'text-cyan-400' :
                                'text-zinc-300'
                            }`}>
                                {log}
                            </span>
                        </div>
                    </div>
                ))}
                <div ref={bottomRef} />
             </div>
        </div>
    </div>
  );
};
