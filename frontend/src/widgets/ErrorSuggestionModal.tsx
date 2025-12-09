import { AlertTriangle, X, RefreshCw, Settings2, Sparkles } from 'lucide-react';
import { useAppStore } from '../entities/store';
import { useState, useEffect } from 'react';

export const ErrorSuggestionModal = () => {
    const { status, setStatus, error } = useAppStore();
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        if (status === 'error') {
            setIsOpen(true);
        }
    }, [status]);

    const handleClose = () => {
        setIsOpen(false);
        setStatus('idle');
    };

    if (!isOpen) return null;

    return (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-6 animate-in fade-in duration-300">
            <div className="bg-[#1f2126] w-full max-w-md rounded-2xl border border-error/20 shadow-2xl p-6 relative">
                <button 
                    onClick={handleClose} 
                    className="absolute top-4 right-4 text-muted hover:text-white transition-colors"
                >
                    <X size={20}/>
                </button>
                
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-error/10 flex items-center justify-center">
                        <AlertTriangle size={20} className="text-error" />
                    </div>
                    <h3 className="text-lg font-bold text-white">Генерация не удалась</h3>
                </div>

                <p className="text-sm text-zinc-300 mb-6 leading-relaxed">
                    Агент столкнулся с критической ошибкой. Это часто происходит из-за перегрузки бесплатной модели или сложного запроса.
                </p>

                <div className="space-y-3">
                    <div className="p-3 bg-white/5 rounded-xl border border-white/5 flex items-start gap-3">
                        <Settings2 size={16} className="text-[#00b67a] mt-0.5" />
                        <div>
                            <h4 className="text-xs font-bold text-white mb-1">Смените модель</h4>
                            <p className="text-[10px] text-muted">
                                Бесплатные модели (GigaChat 3) менее стабильны. Попробуйте <b>Qwen 3 Coder</b> в настройках.
                            </p>
                        </div>
                    </div>

                    <div className="p-3 bg-white/5 rounded-xl border border-white/5 flex items-start gap-3">
                        <Sparkles size={16} className="text-purple-400 mt-0.5" />
                        <div>
                            <h4 className="text-xs font-bold text-white mb-1">Упростите запрос</h4>
                            <p className="text-[10px] text-muted">
                                Попробуйте использовать кнопку <b>AI Enhance</b> для структурирования задачи.
                            </p>
                        </div>
                    </div>
                </div>

                <div className="mt-6 flex gap-3">
                    <button 
                        onClick={handleClose}
                        className="flex-1 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-sm font-medium text-zinc-300 transition-colors"
                    >
                        Закрыть
                    </button>
                    <button 
                        onClick={handleClose}
                        className="flex-1 py-3 rounded-xl bg-[#00b67a] hover:bg-[#00a36d] text-sm font-bold text-white flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-emerald-900/20"
                    >
                        <RefreshCw size={16} /> Попробовать снова
                    </button>
                </div>
            </div>
        </div>
    );
};
