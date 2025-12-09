import { AlertTriangle, X, RefreshCw, Settings2, Sparkles, BrainCircuit } from 'lucide-react';
import { useAppStore, AVAILABLE_MODELS } from '../entities/store';
import { useState, useEffect } from 'react';

export const ErrorSuggestionModal = () => {
    const { status, setStatus, selectedModel, setSelectedModel, logs } = useAppStore();
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

    const handleSwitchModel = () => {
        setSelectedModel('Qwen/Qwen3-Coder-480B-A35B-Instruct');
        handleClose();
    };

    if (!isOpen) return null;

    const currentModelInfo = AVAILABLE_MODELS.find(m => m.id === selectedModel);
    const isFreeModel = currentModelInfo?.isFree || selectedModel.includes('Lite') || selectedModel.includes('GigaChat');
    
    const logText = logs.join(' ').toLowerCase();
    const isContextError = logText.includes('context') || logText.includes('length') || logText.includes('token');
    const isNetworkError = logText.includes('timeout') || logText.includes('connection') || logText.includes('500');

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
                    <div>
                        <h3 className="text-lg font-bold text-white">Генерация остановлена</h3>
                        <p className="text-xs text-error">{currentModelInfo?.name || selectedModel}</p>
                    </div>
                </div>

                <p className="text-sm text-zinc-300 mb-6 leading-relaxed">
                    {isNetworkError 
                        ? "Возникли проблемы с подключением к API модели. Это может быть временный сбой Cloud.ru."
                        : "Агент не смог сгенерировать валидный код за отведенное количество попыток."
                    }
                </p>

                <div className="space-y-3">
                    {isFreeModel && (
                        <div 
                            onClick={handleSwitchModel}
                            className="p-3 bg-white/5 hover:bg-white/10 cursor-pointer transition-colors rounded-xl border border-white/5 flex items-start gap-3 group"
                        >
                            <Settings2 size={16} className="text-[#00b67a] mt-0.5" />
                            <div>
                                <h4 className="text-xs font-bold text-white mb-1 group-hover:text-[#00b67a] transition-colors">Смените модель на Qwen 3 Coder</h4>
                                <p className="text-[10px] text-muted">
                                    Вы используете экспериментальную модель. <b>Qwen 3 Coder</b> лучше справляется со сложным кодом.
                                </p>
                            </div>
                        </div>
                    )}

                    {(isContextError || !isFreeModel) && (
                        <div className="p-3 bg-white/5 rounded-xl border border-white/5 flex items-start gap-3">
                            <Sparkles size={16} className="text-purple-400 mt-0.5" />
                            <div>
                                <h4 className="text-xs font-bold text-white mb-1">Упростите запрос</h4>
                                <p className="text-[10px] text-muted">
                                    Попробуйте разбить задачу на несколько частей или используйте <b>AI Enhance</b> для структурирования.
                                </p>
                            </div>
                        </div>
                    )}

                     {!isNetworkError && !isContextError && !isFreeModel && (
                        <div className="p-3 bg-white/5 rounded-xl border border-white/5 flex items-start gap-3">
                            <BrainCircuit size={16} className="text-blue-400 mt-0.5" />
                            <div>
                                <h4 className="text-xs font-bold text-white mb-1">Сложная логика</h4>
                                <p className="text-[10px] text-muted">
                                    Агент запутался в проверках. Попробуйте добавить в запрос явные шаги (Step 1, Step 2).
                                </p>
                            </div>
                        </div>
                     )}
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
