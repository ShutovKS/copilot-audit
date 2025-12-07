import { Layers, Box, TerminalSquare, Info, Loader2 } from 'lucide-react';
import { useAppStore } from '../entities/store';

export const Sidebar = () => {
  const { input, setInput, setCode, setStatus, addLog, clearLogs, status } = useAppStore();
  
  const handleGenerate = async () => {
    if (!input.trim()) return;
    
    setStatus('processing');
    clearLogs();
    setCode('# Generating...');
    addLog('System: Connecting to Agent Stream...');

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    try {
        const response = await fetch(`${API_URL}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_request: input })
        });
        if (!response.ok) throw new Error("API Error");
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        if (reader) {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');
                for (const line of lines) {
                     if (line.startsWith('data: ')) {
                         try {
                             const data = JSON.parse(line.replace('data: ', ''));
                             if (data.type === 'log') addLog(data.content);
                             if (data.type === 'code') setCode(data.content);
                             if (data.type === 'status' && data.content === 'COMPLETED') setStatus('success');
                             if (data.type === 'error') setStatus('error');
                         } catch(e) {}
                     }
                }
            }
        }
    } catch (e) {
        setStatus('error');
        addLog(`Error: ${e}`);
    }
  };

  const isProcessing = status === 'processing';
  const isDisabled = isProcessing || !input.trim();

  return (
    <div className="bg-[#1f2126] rounded-2xl h-full flex flex-col overflow-hidden shadow-2xl border border-white/5">
       {/* Card Header */}
       <div className="p-6 pb-2">
          <div className="flex items-center gap-3 mb-1">
             <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-[#1f2126]">
                 <span className="font-bold text-sm">1</span>
             </div>
             <h2 className="text-lg font-medium text-white">Конфигурация теста</h2>
          </div>
          <p className="text-xs text-muted pl-11">Настройте параметры генерации</p>
       </div>
       
       <div className="flex-1 p-6 space-y-6 overflow-y-auto">
          
          {/* Input Block */}
          <div className="space-y-2">
            <div className="flex justify-between">
                <label className="text-xs font-medium text-muted">Требования / Swagger</label>
                <span className="text-[10px] text-muted opacity-50">0/2000</span>
            </div>
            <div className="bg-[#18191d] rounded-xl p-1 border border-white/5 focus-within:border-primary/50 transition-colors">
                <textarea 
                    className="w-full h-48 bg-transparent border-none text-sm text-white p-3 focus:ring-0 resize-none placeholder:text-zinc-600"
                    placeholder="Введите описание теста..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={isProcessing}
                />
            </div>
          </div>

          {/* Selector Block */}
          <div className="space-y-2">
             <label className="text-xs font-medium text-muted">Тип тестов</label>
             <div className="bg-[#18191d] p-1 rounded-xl flex gap-1">
                 <button className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-[#2b2d33] text-white text-xs font-medium shadow-sm transition-all">
                     <Layers size={14} /> UI (E2E)
                 </button>
                 <button className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg hover:bg-white/5 text-muted hover:text-white text-xs font-medium transition-all">
                     <Box size={14} /> API (Rest)
                 </button>
             </div>
          </div>

          {/* Info Block */}
          <div className="flex items-start gap-3 p-4 rounded-xl bg-[#2b2d33]/50 border border-white/5">
              <Info size={16} className="text-muted mt-0.5 shrink-0" />
              <div className="space-y-1">
                  <p className="text-xs text-white font-medium">Подсказка</p>
                  <p className="text-[10px] text-muted leading-relaxed">
                      Используйте ссылку на Swagger JSON для более точной генерации API тестов.
                  </p>
              </div>
          </div>
       </div>

       {/* Action Footer */}
       <div className="p-6 pt-0">
          <button 
            onClick={handleGenerate}
            disabled={isDisabled}
            className={`w-full h-12 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2
                ${isDisabled 
                    ? 'bg-[#2b2d33] text-zinc-500 cursor-not-allowed border border-white/5' 
                    : 'bg-primary text-[#131418] hover:bg-primaryHover hover:shadow-lg hover:shadow-primary/20'}
            `}
          >
            {isProcessing ? (
                <>
                    <Loader2 size={18} className="animate-spin" />
                    <span>Генерация...</span>
                </>
            ) : (
                <>
                    <TerminalSquare size={18} />
                    <span>Создать тест</span>
                </>
            )}
          </button>
       </div>
    </div>
  );
};
