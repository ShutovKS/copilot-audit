import Editor from '@monaco-editor/react';
import { useAppStore } from '../entities/store';
import { Copy, Share2, FileCode, Check, Loader2, X, GitMerge } from 'lucide-react';
import { useState } from 'react';
import { exportToGitLab } from '../shared/api/client';

export const CodeEditor = () => {
  const { code } = useAppStore();
  const [copied, setCopied] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportResult, setExportResult] = useState<{url: string} | null>(null);

  // Form State
  const [projectId, setProjectId] = useState('');
  const [token, setToken] = useState('');
  const [gitlabUrl, setGitlabUrl] = useState('https://gitlab.com');

  const handleCopy = () => {
      navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = async () => {
      if (!projectId || !token) return;
      setIsExporting(true);
      try {
          const data = await exportToGitLab(code, projectId, token, gitlabUrl);
          setExportResult({ url: data.mr_url });
      } catch (e) {
          alert('Export failed: ' + e);
      } finally {
          setIsExporting(false);
      }
  };

  return (
    <div className="bg-[#1f2126] rounded-2xl h-full flex flex-col overflow-hidden shadow-2xl border border-white/5 relative">
        {/* Toolbar */}
        <div className="h-16 flex items-center px-6 justify-between border-b border-white/5">
            <div className="flex items-center gap-4">
                <div className="w-8 h-8 rounded-lg bg-[#2b2d33] flex items-center justify-center">
                    <FileCode size={18} className="text-primary" />
                </div>
                <div>
                    <h3 className="text-sm font-medium text-white">Результат</h3>
                    <p className="text-[10px] text-muted">generated_test_suite.py</p>
                </div>
            </div>
            
            <div className="flex items-center gap-2">
                <button 
                    onClick={handleCopy}
                    className="flex items-center gap-2 p-1.5 px-3 hover:bg-[#2b2d33] rounded-lg text-muted hover:text-white transition-colors"
                    title="Copy"
                >
                    {copied ? <Check size={18} className="text-success" /> : <Copy size={18} />}
                    {copied && <span className="text-xs text-success">Copied</span>}
                </button>
                
                <button 
                    onClick={() => setIsModalOpen(true)}
                    disabled={!code}
                    className="px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 bg-[#2b2d33] text-white hover:bg-[#363840]"
                >
                    <Share2 size={14} />
                    <span>Export</span>
                </button>
            </div>
        </div>
        
        {/* Editor */}
        <div className="flex-1 relative bg-[#18191d] m-4 mt-0 rounded-xl overflow-hidden border border-white/5">
             <Editor
                height="100%"
                defaultLanguage="python"
                theme="vs-dark"
                value={code}
                options={{ readOnly: true, minimap: { enabled: false }, fontSize: 13, fontFamily: 'JetBrains Mono, monospace', padding: { top: 20, bottom: 20 } }}
                onMount={(_editor, monaco) => { 
                    monaco.editor.defineTheme('cloud-rounded', { 
                        base: 'vs-dark', 
                        inherit: true, 
                        rules: [], 
                        colors: { 
                            'editor.background': '#18191d', 
                            'editor.lineHighlightBackground': '#1f2126' 
                        } 
                    }); 
                    monaco.editor.setTheme('cloud-rounded'); 
                }}
            />
        </div>

        {/* GitLab Modal */}
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
