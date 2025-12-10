import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type GenerationStatus = 'idle' | 'processing' | 'success' | 'error';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: number;
}

export interface LogEntry {
    id: string;
    content: string;
    timestamp: string;
    type: 'info' | 'error' | 'success' | 'warning' | 'debug';
}

interface EditorSettings {
    fontSize: number;
    minimap: boolean;
    wordWrap: 'on' | 'off';
}

export interface ModelInfo {
    id: string;
    name: string;
    provider: string;
    context: string;
    isFree?: boolean;
    description?: string;
}

export const AVAILABLE_MODELS: ModelInfo[] = [
    {
        id: 'Qwen/Qwen3-Coder-480B-A35B-Instruct',
        name: 'Qwen 3 Coder',
        provider: 'Qwen',
        context: '256k',
        description: 'Best for Code Generation. Massive context.'
    },
    {
        id: 'Qwen/Qwen3-235B-A22B-Instruct-2507',
        name: 'Qwen 3 235B',
        provider: 'Qwen',
        context: '256k',
        description: 'Balanced performance'
    },
    {
        id: 'Qwen/Qwen3-Next-80B-A3B-Instruct',
        name: 'Qwen 3 Next 80B',
        provider: 'Qwen',
        context: '256k',
        description: 'Fast & Efficient'
    },
    {
        id: 'GigaChat/GigaChat-2-Max',
        name: 'GigaChat 2 Max',
        provider: 'Sber',
        context: '128k',
        description: 'Russian language optimized'
    },
    {
        id: 'ai-sage/GigaChat3-10B-A1.8B',
        name: 'GigaChat 3 10B',
        provider: 'ai-sage',
        context: '256k',
        isFree: true,
        description: 'Experimental Free Model'
    },
    {
        id: 'MiniMaxAI/MiniMax-M2',
        name: 'MiniMax M2',
        provider: 'MiniMaxAI',
        context: '192k',
        description: 'High reasoning capabilities'
    },
    {
        id: 'zai-org/GLM-4.6',
        name: 'GLM 4.6',
        provider: 'Zhipu',
        context: '200k',
        description: 'Strong reasoning'
    },
    {
        id: 'openai/gpt-oss-120b',
        name: 'GPT OSS 120B',
        provider: 'OpenAI',
        context: '128k',
        description: 'Open source GPT variant'
    },
    {
        id: 't-tech/T-pro-it-2.0',
        name: 'T-Pro IT 2.0',
        provider: 'T-Tech',
        context: '32k',
        description: 'Specialized IT model'
    },
    {
        id: 't-tech/T-pro-it-1.0',
        name: 'T-Pro IT 1.0',
        provider: 'T-Tech',
        context: '8k'
    },
    {
        id: 't-tech/T-lite-it-1.0',
        name: 'T-Lite IT 1.0',
        provider: 'T-Tech',
        context: '8k',
        description: 'Lightweight'
    }
];

const DEFAULT_MODEL = 'Qwen/Qwen3-Coder-480B-A35B-Instruct';

interface AppState {
  sessionId: string;
  setSessionId: (id: string) => void;

  currentRunId: number | null;
  setCurrentRunId: (id: number | null) => void;

  messages: ChatMessage[];
  addMessage: (msg: ChatMessage) => void;
  clearMessages: () => void;

  input: string;
  setInput: (val: string | ((prev: string) => string)) => void;
  
  code: string;
  setCode: (val: string) => void;

  testPlan: string;
  setTestPlan: (val: string) => void;
  
  logs: LogEntry[];
  addLog: (content: string) => void;
  clearLogs: () => void;
  
  status: GenerationStatus;
  setStatus: (s: GenerationStatus) => void;
  
  error: string | null;
  setError: (msg: string | null) => void;

  editorSettings: EditorSettings;
  updateEditorSettings: (settings: Partial<EditorSettings>) => void;

  selectedModel: string;
  setSelectedModel: (model: string) => void;

  toast: { message: string; type: 'success' | 'error' | 'info' } | null;
  showToast: (message: string, type: 'success' | 'error' | 'info') => void;
  hideToast: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, _) => ({
      sessionId: crypto.randomUUID(),
      setSessionId: (sessionId) => set({ sessionId }),

      currentRunId: null,
      setCurrentRunId: (currentRunId) => set({ currentRunId }),

      messages: [],
      addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
      clearMessages: () => set({ messages: [] }),

      input: '',
      setInput: (val) => set((state) => ({
          input: typeof val === 'function' ? val(state.input) : val
      })),
      
      code: '# Generated tests will appear here...',
      setCode: (code) => set({ code }),

      testPlan: '',
      setTestPlan: (testPlan) => set({ testPlan }),
      
      logs: [],
      addLog: (content) => {
          let type: LogEntry['type'] = 'info';
          if (content.includes('Error') || content.includes('Failed')) type = 'error';
          else if (content.includes('Success') || content.includes('Valid')) type = 'success';
          else if (content.includes('Analyst') || content.includes('Coder')) type = 'debug';

          // Duplicate to Console
          const prefix = `[Forge]`;
          if (type === 'error') console.error(prefix, content);
          else if (type === 'success') console.info(prefix, content);
          else if (type === 'debug') console.debug(prefix, content);
          else console.log(prefix, content);
          
          const newLog: LogEntry = {
              id: crypto.randomUUID(),
              content,
              timestamp: new Date().toLocaleTimeString(),
              type
          };

          set((state) => ({ logs: [...state.logs, newLog] }));
      },
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

      selectedModel: DEFAULT_MODEL,
      setSelectedModel: (selectedModel) => set({ selectedModel }),

      toast: null,
      showToast: (message, type) => set({ toast: { message, type } }),
      hideToast: () => set({ toast: null }),
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({ 
          editorSettings: state.editorSettings, 
          selectedModel: state.selectedModel,
          sessionId: state.sessionId,
          messages: state.messages 
      }),
      onRehydrateStorage: () => (state) => {
          if (state && !state.sessionId) state.setSessionId(crypto.randomUUID());
      }
    }
  )
);
