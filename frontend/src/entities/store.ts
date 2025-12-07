import { create } from 'zustand';

export type GenerationStatus = 'idle' | 'processing' | 'success' | 'error';

interface AppState {
  input: string;
  setInput: (val: string) => void;
  
  code: string;
  setCode: (val: string) => void;
  
  logs: string[];
  addLog: (log: string) => void;
  clearLogs: () => void;
  
  status: GenerationStatus;
  setStatus: (s: GenerationStatus) => void;
  
  error: string | null;
  setError: (msg: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  input: '',
  setInput: (input) => set({ input }),
  
  code: '# Generated tests will appear here...',
  setCode: (code) => set({ code }),
  
  logs: [],
  addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
  clearLogs: () => set({ logs: [] }),
  
  status: 'idle',
  setStatus: (status) => set({ status }),
  
  error: null,
  setError: (error) => set({ error }),
}));
