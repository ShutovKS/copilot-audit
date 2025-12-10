import { Send, TerminalSquare, Loader2, Zap, ShieldAlert, Smartphone, Wand2, Paperclip, GitBranch, X, Check, Lock, Bot, User } from 'lucide-react';
import { useAppStore } from '../entities/store';
import { useState, useRef, useEffect } from 'react';
import { analyzeSourceCode, analyzeGitRepo } from '../shared/api/client';

export const Sidebar = () => {
  const { input, setInput, clearLogs, status, messages, setCurrentRunId, sendMessage } = useAppStore();
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [showGitInput, setShowGitInput] = useState(false);
  const [gitUrl, setGitUrl] = useState('');
  const isValidGitUrl = gitUrl.match(/^https?:\/\/.+/);
  const [gitToken, setGitToken] = useState('');
  const [isPrivateRepo, setIsPrivateRepo] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);
  
  const handleSendMessage = () => {
    const message = useAppStore.getState().input;
    if (!message.trim()) return;
    
    setInput(''); // Clear input immediately
    sendMessage(message);
  };

  // ... (Helpers remain same)
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
          const contextHeader = `\n\n[ANALYSIS RESULT (${source})]:\n❌ No supported API endpoints found.\n`;
          setInput(prev => prev + contextHeader);
      } else {
          const contextHeader = `\n\n[SOURCE CODE CONTEXT (${source}) - ${count} ENDPOINTS]:\n`;
          setInput(prev => prev + contextHeader + summary);
      }
  };

  const isProcessing = status === 'processing';
  // Check if we are waiting for initial response or streaming
  const isStreaming = isProcessing && messages[messages.length - 1]?.role !== 'assistant';

  return (
    <div className="bg-[#1f2126] rounded-2xl h-full flex flex-col overflow-hidden shadow-2xl border border-white/5">
       {/* Header ... Same */}
       <div className="p-4 border-b border-white/5 flex items-center justify-between bg-[#18191d]">
          <div className="flex items-center gap-2">
             <Bot size={18} className="text-primary" />
             <h2 className="text-sm font-bold text-white">AI Assistant</h2>
          </div>
          <button onClick={() => { clearLogs(); setCurrentRunId(null); useAppStore.getState().clearMessages(); }} className="text-[10px] text-muted hover:text-white px-2 py-1 rounded hover:bg-white/5 transition-colors">
              New Chat
          </button>
       </div>
       
       {/* Chat History */}
       <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
          {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-muted opacity-30 gap-3">
                  <Bot size={48} />
                  <p className="text-xs text-center max-w-[200px]">
                      Готов к работе. Опишите задачу или загрузите код.
                  </p>
              </div>
          )}
          
          {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-secondary/20 text-secondary' : 'bg-primary/20 text-primary'}`}>
                      {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                  </div>
                  <div className={`rounded-2xl p-3 text-xs leading-relaxed max-w-[85%] whitespace-pre-wrap ${msg.role === 'user' ? 'bg-[#2b2d33] text-white rounded-tr-sm' : 'bg-[#18191d] text-zinc-300 rounded-tl-sm border border-white/5'}`}>
                      {msg.content}
                  </div>
              </div>
          ))}
          {isStreaming && (
              <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0">
                      <Loader2 size={14} className="animate-spin" />
                  </div>
                  <div className="bg-[#18191d] rounded-2xl rounded-tl-sm p-3 border border-white/5 flex items-center gap-2">
                      <span className="text-xs text-muted">Working on it... check logs &rarr;</span>
                  </div>
              </div>
          )}
          <div ref={messagesEndRef} />
       </div>

       {/* Input Area ... Same */}
       <div className="p-4 pt-2 bg-[#1f2126] border-t border-white/5 space-y-3">
          {/* Toolbar ... Same */}
          <div className="flex items-center gap-2">
                <button 
                    onClick={() => setShowGitInput(!showGitInput)}
                    disabled={isProcessing}
                    className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
                    title="Git Repo"
                >
                    <GitBranch size={14} />
                </button>
                <button 
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isProcessing}
                    className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
                    title="Upload ZIP"
                >
                    <Paperclip size={14} />
                </button>
                <input type="file" ref={fileInputRef} className="hidden" accept=".zip" onChange={handleFileUpload} />
                
                <button 
                    onClick={handleEnhance} 
                    disabled={isEnhancing || !input.trim()}
                    className="p-1.5 rounded-lg hover:bg-white/5 text-secondary hover:text-white transition-colors ml-auto"
                    title="AI Enhance"
                >
                    <Wand2 size={14} className={isEnhancing ? "animate-spin" : ""} />
                </button>
          </div>

          {/* Git Input Popover ... Same */}
          {showGitInput && (
             <div className="bg-[#18191d] p-3 rounded-xl border border-white/10 flex flex-col gap-2 animate-in slide-in-from-bottom-2">
                 <input 
                    type="text" 
                    value={gitUrl} 
                    onChange={e => setGitUrl(e.target.value)} 
                    placeholder="https://github.com/user/repo"
                    className="w-full bg-black/30 text-[10px] text-white p-2 rounded-lg border border-white/10 outline-none"
                 />
                 <div className="flex gap-2">
                     <button 
                        onClick={() => setIsPrivateRepo(!isPrivateRepo)}
                        className={`flex-1 p-1.5 rounded-lg text-[10px] border ${isPrivateRepo ? 'bg-primary/10 border-primary/50 text-primary' : 'border-white/10 text-muted'}`}
                     >
                         {isPrivateRepo ? 'Private (Token Required)' : 'Public Repo'}
                     </button>
                     <button 
                        onClick={handleGitAnalysis}
                        className="flex-1 bg-primary hover:bg-primaryHover text-white text-[10px] font-bold rounded-lg"
                     >
                        Analyze
                     </button>
                 </div>
                 {isPrivateRepo && (
                     <input 
                        type="password" 
                        value={gitToken} 
                        onChange={e => setGitToken(e.target.value)} 
                        placeholder="Git Token"
                        className="w-full bg-black/30 text-[10px] text-white p-2 rounded-lg border border-white/10 outline-none"
                     />
                 )}
             </div>
          )}

          {/* Message Input ... Same */}
          <div className="relative">
              <textarea 
                  className="w-full bg-[#18191d] border border-white/5 rounded-xl p-3 pr-10 text-sm text-white focus:border-primary/50 focus:ring-0 resize-none placeholder:text-zinc-600 custom-scrollbar outline-none transition-all"
                  placeholder="Отправьте сообщение..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                      }
                  }}
                  rows={3}
                  disabled={isProcessing}
              />
              <button 
                  onClick={handleSendMessage}
                  disabled={!input.trim() || isProcessing}
                  className="absolute right-2 bottom-2 p-2 bg-primary hover:bg-primaryHover text-white rounded-lg disabled:opacity-50 disabled:bg-zinc-700 transition-all"
              >
                  {isProcessing ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              </button>
          </div>
       </div>
    </div>
  );
};
