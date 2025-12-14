import type { StateCreator } from 'zustand';

// Types
export interface ModelInfo {
    id: string;
    name: string;
    provider: string;
    context: string;
    isFree?: boolean;
    description?: string;
}

// Constants
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

// State Interface
export interface SettingsSlice {
    sessionId: string;
    setSessionId: (id: string) => void;
    
    selectedModel: string;
    setSelectedModel: (model: string) => void;
}

// Initial State
const initialSettingsState = {
    sessionId: crypto.randomUUID(),
    selectedModel: DEFAULT_MODEL,
};

// State Creator
export const createSettingsSlice: StateCreator<SettingsSlice, [], [], SettingsSlice> = (set) => ({
    ...initialSettingsState,
    setSessionId: (sessionId) => set({ sessionId }),
    setSelectedModel: (selectedModel) => set({ selectedModel }),
});
