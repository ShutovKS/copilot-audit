import type {StateCreator} from 'zustand';

// Types
export type GenerationStatus = 'idle' | 'processing' | 'success' | 'error' | 'waiting_for_input' | 'waiting_for_approval';

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

// State Interface
export interface ChatSlice {
    currentRunId: number | null;
    setCurrentRunId: (id: number | null) => void;

    messages: ChatMessage[];
    addMessage: (msg: ChatMessage) => void;
    setMessages: (msgs: ChatMessage[]) => void;
    
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
    
    reportUrl: string | null;
    setReportUrl: (url: string | null) => void;
    
    clearChatState: () => void;
}

// Initial State
const initialChatState = {
    currentRunId: null,
    messages: [],
    input: '',
    code: '# Generated tests will appear here...',
    testPlan: '',
    logs: [],
    status: 'idle' as GenerationStatus,
    error: null,
    reportUrl: null,
};

// State Creator
export const createChatSlice: StateCreator<ChatSlice, [], [], ChatSlice> = (set) => ({
    ...initialChatState,
    
    setCurrentRunId: (currentRunId) => set({currentRunId}),
    
    addMessage: (msg) => set((state) => ({messages: [...state.messages, msg]})),
    setMessages: (msgs) => set({messages: msgs}),

    setInput: (val) => set((state) => ({
        input: typeof val === 'function' ? val(state.input) : val
    })),

    setCode: (code) => set({code}),
    setTestPlan: (testPlan) => set({testPlan}),

    addLog: (content) => {
        let type: LogEntry['type'] = 'info';
        if (content.includes('Error:') || content.includes('Execution Failed') || content.includes('FAILED')) type = 'error';
        else if (content.includes('Success') || content.includes('Valid')) type = 'success';
        else if (content.includes('Analyst') || content.includes('Coder')) type = 'debug';

        const newLog: LogEntry = {
            id: crypto.randomUUID(),
            content,
            timestamp: new Date().toLocaleTimeString(),
            type
        };

        set((state) => ({logs: [...state.logs, newLog]}));
    },
    clearLogs: () => set({logs: [], testPlan: ''}),

    setStatus: (status) => set({status}),
    setError: (error) => set({error}),
    
    setReportUrl: (url) => set({reportUrl: url}),
    
    clearChatState: () => {
        set({
            messages: [],
            logs: [],
            code: '# Generated tests will appear here...',
            testPlan: '',
            status: 'idle',
            error: null,
            currentRunId: null,
            reportUrl: null,
        });
    },
});
