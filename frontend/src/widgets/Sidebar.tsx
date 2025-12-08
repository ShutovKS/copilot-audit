import { Box, TerminalSquare, Loader2, Zap, ShieldAlert, Smartphone, Wand2 } from 'lucide-react';
import { useAppStore } from '../entities/store';
import { useState } from 'react';

const PRESETS = {
    UI: `Напиши UI тест на Python (Playwright) для калькулятора Cloud.ru (https://cloud.ru/calculator). \nСценарий:\n1. Открыть страницу.\n2. Добавить сервис 'Виртуальная машина'.\n3. Изменить количество CPU на 4.\n4. Проверить, что цена изменилась.`,
    API: `Сгенерируй API тест для методов GET /v1/instances и POST /v1/instances.\nИспользуй базовый URL: https://compute.api.cloud.ru\nПроверь, что в ответе приходит список машин и статус код 200.\nДобавь негативный тест на 401 (без токена).`
};

export const Sidebar = () => {
  const { input, setInput, setCode, setTestPlan, setStatus, addLog, clearLogs, status } = useAppStore();
  const [isEnhancing, setIsEnhancing] = useState(false);
  
  const handleGenerate = async () => {
    if (!input.trim()) return;
    
    setStatus('processing');
    clearLogs();
    setCode('# Generating...');
    setTestPlan('');
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
                             if (data.type === 'plan') setTestPlan(data.content);
                             if (data.type === 'status' && data.content === 'COMPLETED') setStatus('success');
                             if (data.type === 'finish') setStatus('success');
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

  const handleEnhance = async () => {
      if (!input.trim()) return;
      setIsEnhancing(true);
      try {
          const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
          const res = await fetch(`${API_URL}/enhance`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ prompt: input })
          });
          if (res.ok) {
              const data = await res.json();
              setInput(data.enhanced_prompt);
          }
      } catch (e) {
          console.error(e);
      } finally {
          setIsEnhancing(false);
      }
  };

  const addFeature = (text: string) => {
      setInput(input + (input ? '\n' : '') + text);
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
            <div className="flex justify-between items-center">
                <label className="text-xs font-medium text-muted">Требования / Swagger</label>
                <div className="flex items-center gap-2">
                    <button 
                        onClick={handleEnhance} 
                        disabled={isEnhancing || !input.trim()} 
                        className="flex items-center gap-1 text-[10px] text-secondary hover:text-white disabled:opacity-50 transition-colors"
                        title="Улучшить промпт с помощью AI"
                    >
                        {isEnhancing ? <Loader2 size={10} className="animate-spin" /> : <Wand2 size={10} />}
                        AI Enhance
                    </button>
                    <span className="text-[10px] text-muted opacity-50">{input.length}/2000</span>
                </div>
            </div>
            <div className="bg-[#18191d] rounded-xl p-1 border border-white/5 focus-within:border-primary/50 transition-colors">
                <textarea 
                    className="w-full h-48 bg-transparent border-none text-sm text-white p-3 focus:ring-0 resize-none placeholder:text-zinc-600"
                    placeholder="Введите описание теста..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={isProcessing}
                    maxLength={2000}
                />
            </div>
            
            {/* Quick Actions (AI Features) */}
            <div className="flex flex-wrap gap-2 pt-2">
                <button onClick={() => addFeature('Добавь негативные сценарии.')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 text-[10px] text-zinc-300 transition-colors border border-white/5">
                    <ShieldAlert size={10} className="text-error" /> Негативные тесты
                </button>
                <button onClick={() => addFeature('Проверь мобильную версию (viewport).')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 text-[10px] text-zinc-300 transition-colors border border-white/5">
                    <Smartphone size={10} className="text-blue-400" /> Мобайл
                </button>
                <button onClick={() => addFeature('Используй Page Object Model.')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 text-[10px] text-zinc-300 transition-colors border border-white/5">
                    <Box size={10} className="text-yellow-400" /> POM Pattern
                </button>
            </div>
          </div>

          {/* Presets */}
          <div className="space-y-2">
             <label className="text-xs font-medium text-muted">Быстрые сценарии</label>
             <div className="flex gap-2">
                 <button 
                    onClick={() => setInput(PRESETS.UI)}
                    disabled={isProcessing}
                    className="flex-1 px-3 py-2 bg-[#2b2d33] hover:bg-[#363840] rounded-lg text-[10px] text-white flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
                 >
                     <Zap size={12} className="text-yellow-500" /> UI Калькулятор
                 </button>
                 <button 
                    onClick={() => setInput(PRESETS.API)}
                    disabled={isProcessing}
                    className="flex-1 px-3 py-2 bg-[#2b2d33] hover:bg-[#363840] rounded-lg text-[10px] text-white flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
                 >
                     <Box size={12} className="text-blue-500" /> API Compute
                 </button>
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
