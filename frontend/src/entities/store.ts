import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type GenerationStatus = 'idle' | 'processing' | 'success' | 'error';

interface EditorSettings {
    fontSize: number;
    minimap: boolean;
    wordWrap: 'on' | 'off';
}

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
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({ editorSettings: state.editorSettings }), // Persist only settings
    }
  )
);
