import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type GenerationStatus = 'idle' | 'processing' | 'success' | 'error';

interface EditorSettings {
    fontSize: number;
    minimap: boolean;
    wordWrap: 'on' | 'off';
}

export const AVAILABLE_MODELS = [
    { id: 'Qwen/Qwen2.5-Coder-32B-Instruct', name: 'Qwen 2.5 Coder (Recommended)' },
    { id: 'GigaChat/GigaChat-2-Max', name: 'GigaChat 2 Max' },
    { id: 'ai-sage/GigaChat3-10B-A1.8B', name: 'GigaChat 3 (Free)' },
    { id: 'MiniMaxAI/MiniMax-M2', name: 'MiniMax M2' },
    { id: 'openai/gpt-oss-120b', name: 'GPT OSS 120B' },
    { id: 'Qwen/Qwen3-Coder-480B-A35B-Instruct', name: 'Qwen 3 Coder 480B' },
    { id: 't-tech/T-pro-it-1.0', name: 'T-Pro IT 1.0' }
];

interface AppState {
  input: string;
  setInput: (val: string) => void;
  
  code: string;
  setCode: (val: string) => void;

  testPlan: string;
  setTestPlan: (val: string) => void;
  
  logs: string[];
  addLog: (log: string) => void;
  clearLogs: () => void;
  
  status: GenerationStatus;
  setStatus: (s: GenerationStatus) => void;
  
  error: string | null;
  setError: (msg: string | null) => void;

  // Settings
  editorSettings: EditorSettings;
  updateEditorSettings: (settings: Partial<EditorSettings>) => void;

  selectedModel: string;
  setSelectedModel: (model: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      input: '',
      setInput: (input) => set({ input }),
      
      code: '# Generated tests will appear here...',
      setCode: (code) => set({ code }),

      testPlan: '',
      setTestPlan: (testPlan) => set({ testPlan }),
      
      logs: [],
      addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
      clearLogs: () => set({ logs: [], testPlan: '' }),
      
      status: 'idle',
      setStatus: (status) => set({ status }),
      
      error: null,
      setError: (error) => set({ error }),

      editorSettings: {
          fontSize: 13,
          minimap: false,
          wordWrap: 'on'
      },
      updateEditorSettings: (newSettings) => set((state) => ({
          editorSettings: { ...state.editorSettings, ...newSettings }
      })),

      selectedModel: 'Qwen/Qwen2.5-Coder-32B-Instruct',
      setSelectedModel: (selectedModel) => set({ selectedModel }),
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({ 
          editorSettings: state.editorSettings, 
          selectedModel: state.selectedModel 
      }), 
    }
  )
);
