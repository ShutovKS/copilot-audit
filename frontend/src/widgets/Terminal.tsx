import { Terminal as TerminalIcon, CheckCircle2, AlertCircle, Loader2, Activity } from 'lucide-react';
import { useAppStore } from '../entities/store';
import { useEffect, useRef } from 'react';

export const Terminal = () => {
  const { logs, status } = useAppStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="flex flex-col gap-4 h-full">
        {/* Status Card (Like 'Total' block) */}
        <div className="bg-[#1f2126] rounded-2xl p-6 shadow-xl border border-white/5">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-white">Статус агента</h3>
                <Activity size={16} className="text-muted" />
            </div>
            
            <div className="flex items-center gap-3">
                {status === 'processing' && (
                    <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                        <Loader2 size={20} className="animate-spin text-primary" />
                    </div>
                )}
                {status === 'success' && (
                    <div className="w-10 h-10 rounded-full bg-success/20 flex items-center justify-center">
                        <CheckCircle2 size={20} className="text-success" />
                    </div>
                )}
                {status === 'error' && (
                     <div className="w-10 h-10 rounded-full bg-error/20 flex items-center justify-center">
                        <AlertCircle size={20} className="text-error" />
                    </div>
                )}
                {status === 'idle' && (
                     <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
                        <TerminalIcon size={20} className="text-muted" />
                    </div>
                )}

                <div>
                    <div className="text-2xl font-bold text-white">
                        {status === 'idle' && 'Ожидание'}
                        {status === 'processing' && 'Генерация'}
                        {status === 'success' && 'Успех'}
                        {status === 'error' && 'Ошибка'}
                    </div>
                    <div className="text-[10px] text-muted uppercase tracking-wider">
                        Текущее состояние
                    </div>
                </div>
            </div>
        </div>

        {/* Logs Card (Like 'Details' block) */}
        <div className="flex-1 bg-[#1f2126] rounded-2xl p-0 shadow-xl border border-white/5 flex flex-col overflow-hidden">
             <div className="p-5 border-b border-white/5">
                <h3 className="text-sm font-medium text-white">Лог событий</h3>
             </div>
             <div className="flex-1 overflow-y-auto p-5 space-y-3 scrollbar-thin scrollbar-thumb-white/10">
                {logs.length === 0 && (
                    <div className="text-center mt-10">
                        <div className="text-zinc-600 text-xs">Нет событий</div>
                    </div>
                )}
                {logs.map((log, i) => (
                    <div key={i} className="flex gap-3 text-xs leading-relaxed animate-in fade-in slide-in-from-bottom-1">
                        <div className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${ 
                            log.includes('Error') ? 'bg-error' : 
                            log.includes('Success') ? 'bg-success' : 
                            'bg-zinc-600'
                        }`} />
                        <span className="text-zinc-300">{log}</span>
                    </div>
                ))}
                <div ref={bottomRef} />
             </div>
        </div>
    </div>
  );
};
