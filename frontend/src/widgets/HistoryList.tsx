import { useEffect, useState } from 'react';
import { History, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { useAppStore, type ChatMessage } from '../entities/store';

interface TestRun {
    id: number;
    user_request: string;
    status: string;
    created_at: string;
    generated_code: string | null;
    test_plan: string | null;
}

interface BackendMessage {
    type: 'human' | 'ai' | 'system';
    content: string;
}

interface TestRunDetails extends TestRun {
    messages: BackendMessage[];
}

export const HistoryList = () => {
  const { setInput, setCode, setTestPlan, setCurrentRunId, setMessages, clearLogs, sessionId, showToast } = useAppStore();
  const [history, setHistory] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingRun, setLoadingRun] = useState<number | null>(null);

  const fetchHistory = async () => {
      setLoading(true);
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
        const res = await fetch(`${API_URL}/history`, {
            headers: {
                'X-Session-ID': sessionId
            }
        });
        if (res.ok) {
            const data = await res.json();
            setHistory(data);
        } else {
            showToast('Failed to load history', 'error');
        }
      } catch (e) {
        showToast(`Network Error: ${e.message}`, 'error');
      } finally {
          setLoading(false);
      }
  };

  useEffect(() => {
      if (sessionId) {
          fetchHistory();
      }
  }, [sessionId]);

  const loadRun = async (run: TestRun) => {
      setLoadingRun(run.id);
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
        const res = await fetch(`${API_URL}/history/${run.id}`, {
            headers: {
                'X-Session-ID': sessionId
            }
        });

        if (res.ok) {
            const data: TestRunDetails = await res.json();
            
            // Reset state
            clearLogs();

            // Set new state
            setInput('');
            setCode(data.generated_code || '# No code was generated in this run.');
            setTestPlan(data.test_plan || '');
            setCurrentRunId(data.id);

            const mappedMessages: ChatMessage[] = data.messages.map((msg, index) => ({
                id: `${data.id}-${index}`,
                role: msg.type === 'human' ? 'user' : 'assistant',
                content: msg.content,
                timestamp: new Date(data.created_at).getTime() + index
            }));
            setMessages(mappedMessages);

            showToast(`Loaded session #${run.id}`, 'success');
        } else {
            showToast(`Failed to load session #${run.id}`, 'error');
        }
      } catch (e) {
        showToast(`Network Error: ${e.message}`, 'error');
      } finally {
        setLoadingRun(null);
      }
  };

  return (
    <div className="flex flex-col h-full bg-[#1f2126] rounded-2xl border border-white/5 overflow-hidden">
        <div className="p-4 border-b border-white/5 flex justify-between items-center">
            <div className="flex items-center gap-2">
                <History size={16} className="text-muted" />
                <h3 className="text-sm font-medium text-white">История</h3>
            </div>
            <button onClick={fetchHistory} className="text-[10px] text-primary hover:underline" disabled={loading}>
                {loading ? 'Обновление...' : 'Обновить'}
            </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {loading && <div className="text-center text-xs text-muted p-4">Загрузка...</div>}
            
            {!loading && history.length === 0 && (
                <div className="text-center text-xs text-muted p-4">История пуста</div>
            )}

            {history.map((run) => (
                <div 
                    key={run.id} 
                    onClick={() => loadRun(run)}
                    className="p-3 rounded-lg bg-[#18191d] hover:bg-[#2b2d33] cursor-pointer transition-colors border border-white/5 group relative"
                >
                    {loadingRun === run.id && (
                        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                            <Loader2 size={16} className="text-white animate-spin" />
                        </div>
                    )}
                    <div className="flex justify-between items-start mb-1">
                        <span className="text-[10px] text-muted">
                            {new Date(run.created_at).toLocaleTimeString()} {new Date(run.created_at).toLocaleDateString()}
                        </span>
                        <div title={run.status === 'COMPLETED' ? 'Статус: Успешно' : 'Статус: Ошибка'}>
                            {run.status === 'COMPLETED' ? 
                                <CheckCircle2 size={14} className="text-success" /> :
                                <AlertCircle size={14} className="text-error" />
                            }
                        </div>
                    </div>
                    <p className="text-xs text-zinc-300 line-clamp-2 leading-relaxed">
                        {run.user_request}
                    </p>
                </div>
            ))}
        </div>
    </div>
  );
};
