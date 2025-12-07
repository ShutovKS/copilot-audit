import Editor from '@monaco-editor/react';
import { useAppStore } from '../entities/store';
import { Copy, Share2, FileCode, Check } from 'lucide-react';
import { useState } from 'react';

export const CodeEditor = () => {
  const { code } = useAppStore();
  const [copied, setCopied] = useState(false);
  const [exported, setExported] = useState(false);

  const handleCopy = () => {
      navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
  };

  const handleGitLabExport = () => {
      setExported(true);
      setTimeout(() => setExported(false), 3000);
  };

  return (
    <div className="bg-[#1f2126] rounded-2xl h-full flex flex-col overflow-hidden shadow-2xl border border-white/5">
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
                    className="p-2 hover:bg-[#2b2d33] rounded-lg text-muted hover:text-white transition-colors"
                    title="Copy"
                >
                    {copied ? <Check size={18} className="text-success" /> : <Copy size={18} />}
                </button>
                
                <button 
                    onClick={handleGitLabExport}
                    className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2
                        ${exported 
                            ? 'bg-secondary/20 text-secondary' 
                            : 'bg-[#2b2d33] text-white hover:bg-[#363840]'}
                    `}
                >
                    <Share2 size={14} />
                    {exported ? 'Отправлено' : 'GitLab Push'}
                </button>
            </div>
        </div>
        
        {/* Editor Area */}
        <div className="flex-1 relative bg-[#18191d] m-4 mt-0 rounded-xl overflow-hidden border border-white/5">
             <Editor
                height="100%"
                defaultLanguage="python"
                theme="vs-dark"
                value={code}
                options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    fontSize: 13,
                    fontFamily: 'JetBrains Mono, monospace',
                    scrollBeyondLastLine: false,
                    padding: { top: 20, bottom: 20 },
                    lineHeight: 1.6,
                    renderWhitespace: 'selection',
                }}
                onMount={(_editor, monaco) => {
                    monaco.editor.defineTheme('cloud-rounded', {
                        base: 'vs-dark',
                        inherit: true,
                        rules: [],
                        colors: {
                            'editor.background': '#18191d',
                            'editor.lineHighlightBackground': '#1f2126',
                        }
                    });
                    monaco.editor.setTheme('cloud-rounded');
                }}
            />
        </div>
    </div>
  );
};
