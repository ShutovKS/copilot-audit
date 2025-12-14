import type { StateCreator } from 'zustand';

// Types
export type EditorFile = 'code' | 'plan' | 'report';

interface EditorSettings {
    fontSize: number;
    minimap: boolean;
    wordWrap: 'on' | 'off';
}

export interface DebugContextResponse {
    summary: string;
    original_error: string;
    dom_snapshot: string;
    network_errors: string[];
    console_logs: string[];
    hypothesis: string | null;
}

// State Interface
export interface UiSlice {
    toast: { message: string; type: 'success' | 'error' | 'info' } | null;
    showToast: (message: string, type: 'success' | 'error' | 'info') => void;
    hideToast: () => void;

    debugContext: DebugContextResponse | null;
    isDebugReportOpen: boolean;
    showDebugReport: (context: DebugContextResponse) => void;
    hideDebugReport: () => void;

    activeEditorFile: EditorFile;
    setActiveEditorFile: (file: EditorFile) => void;
    
    editorSettings: EditorSettings;
    updateEditorSettings: (settings: Partial<EditorSettings>) => void;
}

// Initial State
const initialUiState = {
    toast: null,
    debugContext: null,
    isDebugReportOpen: false,
    activeEditorFile: 'code' as EditorFile,
    editorSettings: {
        fontSize: 13,
        minimap: false,
        wordWrap: 'on' as 'on' | 'off',
    },
};

// State Creator
export const createUiSlice: StateCreator<UiSlice, [], [], UiSlice> = (set) => ({
    ...initialUiState,

    showToast: (message, type) => set({ toast: { message, type } }),
    hideToast: () => set({ toast: null }),

    showDebugReport: (context) => set({ debugContext: context, isDebugReportOpen: true }),
    hideDebugReport: () => set({ isDebugReportOpen: false, debugContext: null }),

    setActiveEditorFile: (file) => set({ activeEditorFile: file }),
    
    updateEditorSettings: (newSettings) => set((state) => ({
        editorSettings: { ...state.editorSettings, ...newSettings }
    })),
});
