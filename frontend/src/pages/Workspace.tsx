import { useState } from 'react';
import { Sidebar } from '../widgets/Sidebar';
import { CodeEditor } from '../widgets/Editor';
import { Terminal } from '../widgets/Terminal';
import { HistoryList } from '../widgets/HistoryList';
import { SettingsModal } from '../widgets/SettingsModal';
import { ErrorSuggestionModal } from '../widgets/ErrorSuggestionModal';

export const Workspace = () => {
  const [activeTab, setActiveTab] = useState<'config' | 'history'>('config');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#131418] p-4 gap-4 overflow-hidden font-sans relative">
        <div className="w-[400px] flex-shrink-0 flex flex-col gap-2">
            <div className="flex bg-[#1f2126] p-1 rounded-xl border border-white/5 shrink-0">
                <button 
                    onClick={() => setActiveTab('config')}
                    className={`flex-1 py-2 text-xs font-medium rounded-lg transition-all ${activeTab === 'config' ? 'bg-[#2b2d33] text-white shadow-sm' : 'text-muted hover:text-white'}`}
                >
                    Конфигурация
                </button>
                <button 
                    onClick={() => setActiveTab('history')}
                    className={`flex-1 py-2 text-xs font-medium rounded-lg transition-all ${activeTab === 'history' ? 'bg-[#2b2d33] text-white shadow-sm' : 'text-muted hover:text-white'}`}
                >
                    История
                </button>
            </div>

            <div className="flex-1 min-h-0">
                {activeTab === 'config' ? <Sidebar /> : <HistoryList />}
            </div>
        </div>

        <div className="flex-1 flex flex-col min-w-0">
            <CodeEditor />
        </div>

        <div className="w-[340px] flex-shrink-0 flex flex-col">
            <Terminal onOpenSettings={() => setIsSettingsOpen(true)} />
        </div>

        <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        <ErrorSuggestionModal />
    </div>
  );
};
