import { X, Server, Database, BrainCircuit, CheckCircle2, XCircle, RefreshCw, Loader2, Type, LayoutTemplate } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAppStore } from '../entities/store';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

interface SystemStatus {
    service: string;
    version: string;
    database: string;
    llm: string;
}

export const SettingsModal = ({ isOpen, onClose }: SettingsModalProps) => {
    const { editorSettings, updateEditorSettings } = useAppStore();
    const [status, setStatus] = useState<SystemStatus | null>(null);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<'system' | 'editor'>('system');

    const checkHealth = async () => {
        setLoading(true);
        try {
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
            const res = await fetch(`${API_URL}/health`);
            if (res.ok) {
                const data = await res.json();
                setStatus(data);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen && activeTab === 'system') checkHealth();
    }, [isOpen, activeTab]);

    if (!isOpen) return null;

    return (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
            <div className="bg-[#1f2126] w-full max-w-md rounded-2xl border border-white/10 shadow-2xl p-0 relative overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-white/5">
                     <div className="flex gap-4">
                        <button 
                            onClick={() => setActiveTab('system')}
                            className={`text-sm font-medium transition-colors ${activeTab === 'system' ? 'text-white' : 'text-muted hover:text-white'}`}
                        >
                            System
                        </button>
                        <button 
                            onClick={() => setActiveTab('editor')}
                            className={`text-sm font-medium transition-colors ${activeTab === 'editor' ? 'text-white' : 'text-muted hover:text-white'}`}
                        >
                            Editor
                        </button>
                     </div>
                     <button onClick={onClose} className="text-muted hover:text-white"><X size={20}/></button>
                </div>

                <div className="p-6">
                    {activeTab === 'system' ? (
                        <div className="space-y-4">
                            {/* System Status Content (Same as before) */}
                            <div className="flex items-center justify-between p-3 bg-[#18191d] rounded-xl border border-white/5">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-500">
                                        <Server size={16} />
                                    </div>
                                    <div>
                                        <div className="text-xs font-medium text-zinc-400">Backend API</div>
                                        <div className="text-sm font-bold text-white">{status?.version || '...'}</div>
                                    </div>
                                </div>
                                {status ? <CheckCircle2 size={18} className="text-success" /> : <Loader2 size={18} className="animate-spin text-muted" />}
                            </div>

                            <div className="flex items-center justify-between p-3 bg-[#18191d] rounded-xl border border-white/5">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center text-purple-500">
                                        <Database size={16} />
                                    </div>
                                    <div>
                                        <div className="text-xs font-medium text-zinc-400">Database</div>
                                        <div className="text-sm font-bold text-white capitalize">{status?.database || 'checking...'}</div>
                                    </div>
                                </div>
                                {status?.database === 'connected' ? 
                                    <CheckCircle2 size={18} className="text-success" /> : 
                                    (loading ? <Loader2 size={18} className="animate-spin text-muted" /> : <XCircle size={18} className="text-error" />)
                                }
                            </div>

                            <div className="flex items-center justify-between p-3 bg-[#18191d] rounded-xl border border-white/5">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center text-green-500">
                                        <BrainCircuit size={16} />
                                    </div>
                                    <div>
                                        <div className="text-xs font-medium text-zinc-400">Cloud.ru Evolution</div>
                                        <div className="text-sm font-bold text-white capitalize">{status?.llm || 'checking...'}</div>
                                    </div>
                                </div>
                                {status?.llm === 'ready' ? 
                                    <CheckCircle2 size={18} className="text-success" /> : 
                                    (loading ? <Loader2 size={18} className="animate-spin text-muted" /> : <XCircle size={18} className="text-error" />)
                                }
                            </div>
                            
                            <button 
                                onClick={checkHealth}
                                disabled={loading}
                                className="w-full mt-6 py-3 rounded-xl bg-[#2b2d33] hover:bg-[#363840] text-sm font-medium text-white flex items-center justify-center gap-2 transition-colors"
                            >
                                <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
                                Refresh Status
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Editor Settings */}
                            <div>
                                <label className="block text-xs font-bold text-muted uppercase mb-3 flex items-center gap-2">
                                    <Type size={14} /> Font Size
                                </label>
                                <div className="flex gap-2">
                                    {[12, 13, 14, 16, 18].map(size => (
                                        <button
                                            key={size}
                                            onClick={() => updateEditorSettings({ fontSize: size })}
                                            className={`w-8 h-8 rounded-lg text-xs font-bold transition-all ${editorSettings.fontSize === size ? 'bg-primary text-[#131418]' : 'bg-[#18191d] text-muted hover:text-white'}`}
                                        >
                                            {size}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-muted uppercase mb-3 flex items-center gap-2">
                                    <LayoutTemplate size={14} /> Minimap
                                </label>
                                <div className="flex bg-[#18191d] p-1 rounded-lg w-fit">
                                    <button 
                                        onClick={() => updateEditorSettings({ minimap: true })}
                                        className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${editorSettings.minimap ? 'bg-[#2b2d33] text-white' : 'text-muted'}`}
                                    >
                                        On
                                    </button>
                                    <button 
                                        onClick={() => updateEditorSettings({ minimap: false })}
                                        className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${!editorSettings.minimap ? 'bg-[#2b2d33] text-white' : 'text-muted'}`}
                                    >
                                        Off
                                    </button>
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-muted uppercase mb-3">Word Wrap</label>
                                <div className="flex bg-[#18191d] p-1 rounded-lg w-fit">
                                    <button 
                                        onClick={() => updateEditorSettings({ wordWrap: 'on' })}
                                        className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${editorSettings.wordWrap === 'on' ? 'bg-[#2b2d33] text-white' : 'text-muted'}`}
                                    >
                                        On
                                    </button>
                                    <button 
                                        onClick={() => updateEditorSettings({ wordWrap: 'off' })}
                                        className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${editorSettings.wordWrap === 'off' ? 'bg-[#2b2d33] text-white' : 'text-muted'}`}
                                    >
                                        Off
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
