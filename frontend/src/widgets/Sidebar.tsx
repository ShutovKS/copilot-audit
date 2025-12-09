import { Box, TerminalSquare, Loader2, Zap, ShieldAlert, Smartphone, Wand2, Paperclip, GitBranch, X, Check, Lock } from 'lucide-react';
import { useAppStore } from '../entities/store';
import { useState, useRef } from 'react';
import { analyzeSourceCode, analyzeGitRepo } from '../shared/api/client';

const PRESETS = {
    UI: `Напиши UI тест на Python (Playwright) для калькулятора Cloud.ru (https://cloud.ru/calculator). \nСценарий:\n1. Открыть страницу.\n2. Добавить сервис 'Виртуальная машина'.\n3. Изменить количество CPU на 4.\n4. Проверить, что цена изменилась.`,
    API: `Сгенерируй API тест для методов GET /v1/instances и POST /v1/instances.\nИспользуй базовый URL: https://compute.api.cloud.ru\nПроверь, что в ответе приходит список машин и статус код 200.\nДобавь негативный тест на 401 (без токена).`
};

export const Sidebar = () => {
  const { input, setInput, setCode, setTestPlan, setStatus, addLog, clearLogs, status, selectedModel, sessionId, showToast } = useAppStore();
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [showGitInput, setShowGitInput] = useState(false);
  const [gitUrl, setGitUrl] = useState('');
  const isValidGitUrl = gitUrl.match(/^https?:\/\/.+/);
  const [gitToken, setGitToken] = useState('');
  const [isPrivateRepo, setIsPrivateRepo] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const handleGenerate = async () => {
    if (!input.trim()) return;
    
    setStatus('processing');
    clearLogs();
    setCode('# Generating...');
    setTestPlan('');
    addLog(`System: Connecting to Agent Stream using ${selectedModel}...`);

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    try {
        const response = await fetch(`${API_URL}/generate`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId
            },
            body: JSON.stringify({ 
                user_request: input,
                model_name: selectedModel
            })
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
                             if (data.type === 'error') {
                                 setStatus('error');
                                 addLog(`Error: ${data.content}`);
                             }
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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      if (!file.name.endsWith('.zip')) { alert('Please upload a .zip file'); return; }
      setIsUploading(true);
      try {
          const result = await analyzeSourceCode(file);
          appendContext(result.summary, result.endpoint_count, file.name);
      } catch (e) { showToast('Failed to analyze source code. See logs.', 'error'); console.error(e); }
      finally { setIsUploading(false); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };

  const handleGitAnalysis = async () => {
      if (!gitUrl.trim()) return;
      setIsUploading(true);
      try {
          const token = isPrivateRepo && gitToken ? gitToken : undefined;
          const result = await analyzeGitRepo(gitUrl, token);
          appendContext(result.summary, result.endpoint_count, gitUrl);
          setShowGitInput(false);
          setGitUrl('');
          setGitToken('');
          setIsPrivateRepo(false);
      } catch (e) { showToast('Failed to clone/analyze repo. Check URL or Token.', 'error'); console.error(e); }
      finally { setIsUploading(false); }
  };

  const appendContext = (summary: string, count: number, source: string) => {
      if (count === 0) {
          showToast(
              "⚠️ No API endpoints found!\n\nSupported Frameworks:\n• Python: FastAPI\n• Java: Spring Boot\n• Node.js: NestJS, Express\n\nCheck if your code uses standard decorators.", 
              'error'
          );
          
          const contextHeader = `\n\n[ANALYSIS RESULT (${source})]:\n❌ No supported API endpoints found.\nSupported: FastAPI, Spring, NestJS, Express.\n`;
          setInput(prev => prev + contextHeader);
          addLog(`System: Analyzed ${source} but found 0 endpoints.`);
      } else {
          const contextHeader = `\n\n[SOURCE CODE CONTEXT (${source}) - ${count} ENDPOINTS]:\n`;
          setInput(prev => prev + contextHeader + summary);
          addLog(`System: Successfully analyzed ${source}. Found ${count} endpoints.`);
      }
  };

  const addFeature = (text: string) => {
      setInput(input + (input ? '\n' : '') + text);
  };

  const isProcessing = status === 'processing';
  const isDisabled = isProcessing || !input.trim();

  return (
    <div className="bg-[#1f2126] rounded-2xl h-full flex flex-col overflow-hidden shadow-2xl border border-white/5">
       <div className="p-6 pb-2">
          <div className="flex items-center gap-3 mb-1">
             <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-[#1f2126]">
                 <span className="font-bold text-sm">1</span>
             </div>
             <h2 className="text-lg font-medium text-white">Конфигурация</h2>
          </div>
          <p className="text-xs text-muted pl-11">Настройте параметры генерации</p>
       </div>
       
       <div className="flex-1 p-6 space-y-6 overflow-y-auto">
          
          <div className="space-y-2">
            <div className="flex justify-between items-center">
                <label className="text-xs font-medium text-muted">Требования / Swagger</label>
                
                {/* Added 'relative' here to anchor the absolute popover */}
                <div className="flex items-center gap-2 relative">
                    {showGitInput ? (
                        <div className="flex flex-col gap-2 p-3 bg-[#18191d] rounded-xl border border-white/10 animate-in slide-in-from-right-2 duration-200 z-50 absolute right-0 top-0 shadow-2xl w-72">
                            <div className="flex justify-between items-center mb-1">
                                <span className="text-[10px] font-bold text-muted uppercase">Clone Repository</span>
                                <button onClick={() => setShowGitInput(false)} className="text-muted hover:text-white"><X size={12}/></button>
                            </div>
                            
                            <div className="flex items-center gap-2">
                                <input 
                                    type="text" 
                                    value={gitUrl} 
                                    onChange={e => setGitUrl(e.target.value)} 
                                    placeholder="https://github.com/user/repo"
                                    className={`flex-1 bg-black/30 text-[10px] text-white p-2 rounded-lg border outline-none transition-colors 
                                        ${gitUrl && !isValidGitUrl ? 'border-red-500/50 focus:border-red-500' : 'border-white/10 focus:border-primary'}
                                    `}
                                    autoFocus
                                />
                                <button 
                                    onClick={() => setIsPrivateRepo(!isPrivateRepo)}
                                    className={`p-2 rounded-lg hover:bg-white/10 transition-colors ${isPrivateRepo ? 'text-primary bg-primary/10' : 'text-muted'}`}
                                    title="Private Repository?"
                                >
                                    <Lock size={12} />
                                </button>
                            </div>
                            
                            {isPrivateRepo && (
                                <input 
                                    type="password" 
                                    value={gitToken} 
                                    onChange={e => setGitToken(e.target.value)} 
                                    placeholder="Personal Access Token (PAT)"
                                    className="w-full bg-black/30 text-[10px] text-white p-2 rounded-lg border border-white/10 focus:border-primary outline-none animate-in fade-in slide-in-from-top-1"
                                />
                            )}

                            <button 
                                onClick={handleGitAnalysis} 
                                disabled={isUploading || !isValidGitUrl}
                                className={`w-full py-2.5 mt-2 bg-[#00b67a] text-white text-[11px] font-bold rounded-lg flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-900/20
                                    ${(isUploading || !isValidGitUrl) ? 'opacity-50 cursor-not-allowed grayscale' : 'hover:bg-[#00a36d] hover:scale-[1.02] active:scale-[0.98]'}
                                `}
                            >
                                {isUploading ? <Loader2 size={14} className="animate-spin"/> : <GitBranch size={14}/>} 
                                Analyze Repository
                            </button>
                        </div>
                    ) : (
                        <>
                            <button 
                                onClick={() => setShowGitInput(true)}
                                disabled={isUploading || isProcessing}
                                className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-white disabled:opacity-50 transition-colors"
                                title="Clone Git Repo"
                            >
                                <GitBranch size={10} /> Git
                            </button>
                            <div className="h-3 w-px bg-white/10 mx-1" />
                            <button 
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isUploading || isProcessing}
                                className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-white disabled:opacity-50 transition-colors"
                                title="Upload ZIP"
                            >
                                <Paperclip size={10} /> {isUploading ? '...' : 'ZIP'}
                            </button>
                        </>
                    )}
                    
                    <input type="file" ref={fileInputRef} className="hidden" accept=".zip" onChange={handleFileUpload} />
                    
                    <div className="h-3 w-px bg-white/10 mx-1" />

                    <button 
                        onClick={handleEnhance} 
                        disabled={isEnhancing || !input.trim()} 
                        className="flex items-center gap-1 text-[10px] text-secondary hover:text-white disabled:opacity-50 transition-colors"
                    >
                        {isEnhancing ? <Loader2 size={10} className="animate-spin" /> : <Wand2 size={10} />}
                        AI Enhance
                    </button>
                </div>
            </div>
            <div className="bg-[#18191d] rounded-xl p-1 border border-white/5 focus-within:border-primary/50 transition-colors">
                <textarea 
                    className="w-full h-48 bg-transparent border-none text-sm text-white p-3 focus:ring-0 resize-none placeholder:text-zinc-600"
                    placeholder="Введите требования или загрузите код..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={isProcessing}
                    maxLength={10000}
                />
            </div>
            
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

       <div className="p-6 pt-0">
          <button 
            onClick={handleGenerate}
            disabled={isDisabled}
            className={`w-full h-12 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2
                ${isDisabled 
                    ? 'bg-[#2b2d33] text-zinc-500 cursor-not-allowed border border-white/5' 
                    : 'bg-[#00b67a] hover:bg-[#00a36d] text-white hover:shadow-[0_0_20px_rgba(0,182,122,0.4)] hover:scale-[1.02] active:scale-[0.98]'}
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
