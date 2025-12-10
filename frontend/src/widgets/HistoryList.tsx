import { useEffect, useState } from 'react';
import { History, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAppStore } from '../entities/store';

interface TestRun {
    id: number;
    user_request: string;
    status: string;
    created_at: string;
    generated_code: string | null;
    test_plan: string | null;
}

export const HistoryList = () => {
  const { setInput, setCode, setTestPlan, setCurrentRunId, sessionId } = useAppStore();
  const [history, setHistory] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(false);

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
        }
      } finally {
          setLoading(false);
      }
  };

  useEffect(() => {
      if (sessionId) {
          fetchHistory();
      }
  }, [sessionId]);

  const loadRun = (run: TestRun) => {
      if (run.user_request) setInput(run.user_request);
      if (run.generated_code) setCode(run.generated_code);
      if (run.test_plan) setTestPlan(run.test_plan);
      setCurrentRunId(run.id);
  };

  return (
    <div className="flex flex-col h-full bg-[#1f2126] rounded-2xl border border-white/5 overflow-hidden">
        <div className="p-4 border-b border-white/5 flex justify-between items-center">
            <div className="flex items-center gap-2">
                <History size={16} className="text-muted" />
                <h3 className="text-sm font-medium text-white">История</h3>
            </div>
            <button onClick={fetchHistory} className="text-[10px] text-primary hover:underline">Обновить</button>
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
                    className="p-3 rounded-lg bg-[#18191d] hover:bg-[#2b2d33] cursor-pointer transition-colors border border-white/5 group"
                >
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
