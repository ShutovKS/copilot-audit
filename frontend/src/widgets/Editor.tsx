import Editor from '@monaco-editor/react';
import { useAppStore } from '../entities/store';
import { Copy, Check, Loader2, X, GitMerge, FileText, Code2 } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { exportToGitLab } from '../shared/api/client';

export const CodeEditor = () => {
  const { code: storeCode, testPlan, editorSettings } = useAppStore();
  const [displayCode, setDisplayCode] = useState('');
  const [activeFile, setActiveFile] = useState<'code' | 'plan'>('code');
  const [copied, setCopied] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportResult, setExportResult] = useState<{url: string} | null>(null);

  const [projectId, setProjectId] = useState('');
  const [token, setToken] = useState('');
  const [gitlabUrl, setGitlabUrl] = useState('https://gitlab.com');

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const currentIndexRef = useRef(0);
  const targetCodeRef = useRef('');

  useEffect(() => {
      if (storeCode !== targetCodeRef.current) {
          if (targetCodeRef.current === '' || storeCode.length < targetCodeRef.current.length) {
             setDisplayCode('');
             currentIndexRef.current = 0;
          }
          targetCodeRef.current = storeCode;
          if (!intervalRef.current) {
              intervalRef.current = setInterval(() => {
                  const target = targetCodeRef.current;
                  const current = currentIndexRef.current;
                  if (current < target.length) {
                      const chunk = target.slice(current, current + 15); // Faster typing
                      setDisplayCode(prev => prev + chunk);
                      currentIndexRef.current += 15;
                  } else {
                      setDisplayCode(target);
                      if (intervalRef.current) {
                          clearInterval(intervalRef.current);
                          intervalRef.current = null;
                      }
                  }
              }, 5);
          }
      }
  }, [storeCode]);

  const handleCopy = () => {
      navigator.clipboard.writeText(activeFile === 'code' ? storeCode : testPlan);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = async () => {
      if (!projectId || !token) return;
      setIsExporting(true);
      try {
          const data = await exportToGitLab(storeCode, projectId, token, gitlabUrl);
          setExportResult({ url: data.mr_url });
      } catch (e) {
          alert('Export failed: ' + e);
      } finally {
          setIsExporting(false);
      }
  };

  return (
    <div className="bg-[#1f2126] rounded-2xl h-full flex flex-col overflow-hidden shadow-2xl border border-white/5 relative">
        <div className="h-12 flex items-center px-4 justify-between border-b border-white/5 bg-[#18191d]">
             <div className="flex gap-1 h-full pt-2">
                <button 
                    onClick={() => setActiveFile('code')}
                    className={`flex items-center gap-2 px-4 rounded-t-lg text-xs font-medium transition-all ${activeFile === 'code' ? 'bg-[#1f2126] text-white border-t border-x border-white/5' : 'text-muted hover:text-white hover:bg-[#1f2126]/50'}`}
                >
                    <Code2 size={14} className="text-blue-400" /> generated_test.py
                </button>
                <button 
                    onClick={() => setActiveFile('plan')}
                    className={`flex items-center gap-2 px-4 rounded-t-lg text-xs font-medium transition-all ${activeFile === 'plan' ? 'bg-[#1f2126] text-white border-t border-x border-white/5' : 'text-muted hover:text-white hover:bg-[#1f2126]/50'}`}
                >
                    <FileText size={14} className="text-yellow-400" /> test_plan.md
                </button>
             </div>

             <div className="flex items-center gap-2 mb-1">
                <button 
                    onClick={handleCopy}
                    className="p-1.5 hover:bg-[#2b2d33] rounded-md text-muted hover:text-white transition-colors"
                    title="Copy"
                >
                    {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
                </button>
                <button 
                    onClick={() => setIsModalOpen(true)}
                    disabled={!storeCode}
                    className="flex items-center gap-2 px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary rounded-md text-[10px] font-bold transition-colors"
                >
                    <GitMerge size={12} /> Export
                </button>
             </div>
        </div>

        <div className="flex-1 flex min-h-0">
            <div className="w-48 border-r border-white/5 bg-[#18191d] p-3 hidden md:block">
                <h4 className="text-[10px] font-bold text-muted uppercase tracking-wider mb-3">Explorer</h4>
                <div className="space-y-1">
                    <div 
                        onClick={() => setActiveFile('code')}
                        className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer text-xs ${activeFile === 'code' ? 'bg-[#2b2d33] text-white' : 'text-zinc-400 hover:text-white hover:bg-[#2b2d33]/50'}`}
                    >
                        <Code2 size={14} className="text-blue-400" />
                        <span>test_suite.py</span>
                    </div>
                    <div 
                        onClick={() => setActiveFile('plan')}
                        className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer text-xs ${activeFile === 'plan' ? 'bg-[#2b2d33] text-white' : 'text-zinc-400 hover:text-white hover:bg-[#2b2d33]/50'}`}
                    >
                        <FileText size={14} className="text-yellow-400" />
                        <span>test_plan.md</span>
                    </div>
                </div>
            </div>

            <div className="flex-1 bg-[#1f2126] relative">
                 <Editor
                    height="100%"
                    defaultLanguage={activeFile === 'code' ? 'python' : 'markdown'}
                    theme="vs-dark"
                    value={activeFile === 'code' ? displayCode : (testPlan || '*Test plan not generated yet*')}
                    options={{ 
                        readOnly: true, 
                        minimap: { enabled: editorSettings.minimap }, 
                        fontSize: editorSettings.fontSize, 
                        wordWrap: editorSettings.wordWrap,
                        fontFamily: 'JetBrains Mono, monospace', 
                        padding: { top: 20, bottom: 20 },
                    }}
                    onMount={(_editor, monaco) => { 
                        monaco.editor.defineTheme('cloud-rounded', { 
                            base: 'vs-dark', 
                            inherit: true, 
                            rules: [], 
                            colors: { 
                                'editor.background': '#1f2126', 
                                'editor.lineHighlightBackground': '#2b2d33' 
                            } 
                        }); 
                        monaco.editor.setTheme('cloud-rounded'); 
                    }}
                />
            </div>
        </div>

        {isModalOpen && (
            <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                <div className="bg-[#1f2126] w-full max-w-md rounded-2xl border border-white/10 shadow-2xl p-6">
                    <div className="flex justify-between items-center mb-6">
                        <div className="flex items-center gap-2">
                            <GitMerge className="text-orange-500" />
                            <h3 className="text-lg font-bold text-white">Export to GitLab</h3>
                        </div>
                        <button onClick={() => setIsModalOpen(false)} className="text-muted hover:text-white"><X size={20}/></button>
                    </div>

                    {!exportResult ? (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-muted uppercase mb-1">Project ID</label>
                                <input type="text" className="w-full bg-[#18191d] border border-white/10 rounded-lg p-3 text-sm text-white focus:border-orange-500 outline-none" placeholder="e.g. 54321" value={projectId} onChange={e => setProjectId(e.target.value)} />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-muted uppercase mb-1">Access Token</label>
                                <input type="password" className="w-full bg-[#18191d] border border-white/10 rounded-lg p-3 text-sm text-white focus:border-orange-500 outline-none" placeholder="glpat-..." value={token} onChange={e => setToken(e.target.value)} />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-muted uppercase mb-1">GitLab URL</label>
                                <input type="text" className="w-full bg-[#18191d] border border-white/10 rounded-lg p-3 text-sm text-white focus:border-orange-500 outline-none" value={gitlabUrl} onChange={e => setGitlabUrl(e.target.value)} />
                            </div>
                            
                            <button 
                                onClick={handleExport}
                                disabled={isExporting}
                                className="w-full py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-xl font-bold flex items-center justify-center gap-2 mt-4"
                            >
                                {isExporting ? <Loader2 className="animate-spin"/> : 'Create Merge Request'}
                            </button>
                        </div>
                    ) : (
                        <div className="text-center space-y-4">
                            <div className="w-12 h-12 bg-success/20 rounded-full flex items-center justify-center mx-auto">
                                <Check size={24} className="text-success" />
                            </div>
                            <h4 className="text-white font-bold">Merge Request Created!</h4>
                            <a href={exportResult.url} target="_blank" rel="noreferrer" className="block p-3 bg-[#18191d] rounded-lg text-primary text-sm underline truncate hover:text-white transition-colors">
                                {exportResult.url}
                            </a>
                            <button onClick={() => { setIsModalOpen(false); setExportResult(null); }} className="text-sm text-muted hover:text-white">
                                Close
                            </button>
                        </div>
                    )}
                </div>
            </div>
        )}
    </div>
  );
};
