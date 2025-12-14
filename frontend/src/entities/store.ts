import {create} from 'zustand';
import {persist} from 'zustand/middleware';
import {createChatSlice} from './slices/chatSlice';
import type {ChatSlice} from './slices/chatSlice';
import {createUiSlice} from './slices/uiSlice';
import type {UiSlice} from './slices/uiSlice';
import {createSettingsSlice} from './slices/settingsSlice';
import type {SettingsSlice} from './slices/settingsSlice';
import {chatStreamService} from '../shared/api/ChatStreamService';
import type {StreamEvent} from '../shared/api/ChatStreamService';
import type {DebugContextResponse} from "./slices/uiSlice";

// Root AppState is a combination of all slices
export type AppState = ChatSlice & UiSlice & SettingsSlice & Actions;

// Define actions separately to avoid circular dependencies in slices
interface Actions {
    sendMessage: (message: string) => Promise<void>;
    approvePlan: (params: { approved: boolean; feedback?: string }) => Promise<void>;
    fetchAndShowDebugReport: (runId: number) => Promise<void>;
    clearWorkspace: (hard?: boolean) => Promise<void>;
}


export const useAppStore = create<AppState>()(
    persist(
        (set, get) => ({
            ...createChatSlice(set, get, {} as any),
            ...createUiSlice(set, get, {} as any),
            ...createSettingsSlice(set, get, {} as any),

            // ASYNC ACTIONS //

            sendMessage: async (message: string) => {
                const {
                    addMessage, setStatus, clearLogs, addLog, setCurrentRunId,
                    setCode, setTestPlan, showToast, currentRunId, selectedModel,
                    sessionId,
                } = get();

                addMessage({
                    id: crypto.randomUUID(),
                    role: 'user',
                    content: message,
                    timestamp: Date.now(),
                });

                setStatus('processing');
                if (!currentRunId) clearLogs();
                addLog(`System: Sending message to Chat Agent...`);

                const handleStreamEvent = (data: StreamEvent) => {
                    switch (data.type) {
                        case 'meta':
                            if (data.run_id) setCurrentRunId(data.run_id);
                            break;
                        case 'log':
                            addLog(data.content);
                            break;
                        case 'message':
                            addMessage({
                                id: crypto.randomUUID(),
                                role: 'assistant',
                                content: data.content,
                                timestamp: Date.now(),
                            });
                            break;
                        case 'code':
                            setCode(data.content);
                            break;
                        case 'plan':
                            setTestPlan(data.content);
                            break;
                        case 'status':
                            const newStatus = String(data.content || '').toUpperCase();
                            if (newStatus === 'COMPLETED') setStatus('success');
                            else if (newStatus === 'FAILED') setStatus('error');
                            else if (newStatus === 'WAITING_FOR_INPUT') setStatus('waiting_for_input');
                            else if (newStatus === 'WAITING_FOR_APPROVAL') setStatus('waiting_for_approval');
                            break;
                        case 'finish':
                            const finalStatus = get().status;
                            if (finalStatus !== 'waiting_for_input' && finalStatus !== 'waiting_for_approval') {
                                setStatus('success');
                                showToast("Code Updated Successfully!", 'success');
                                addMessage({
                                    id: crypto.randomUUID(),
                                    role: 'assistant',
                                    content: 'Готово! Я обновил код и план тестирования.',
                                    timestamp: Date.now(),
                                });
                            }
                            break;
                        case 'error':
                            setStatus('error');
                            addLog(`Error: ${data.content}`);
                            addMessage({
                                id: crypto.randomUUID(),
                                role: 'assistant',
                                content: `Ошибка: ${data.content}`,
                                timestamp: Date.now(),
                            });
                            break;
                    }
                };
                
                await chatStreamService.sendMessage({
                    message,
                    modelName: selectedModel,
                    runId: currentRunId,
                    sessionId,
                }, {
                    onData: handleStreamEvent,
                    onError: (error) => {
                        setStatus('error');
                        addLog(`Error: ${error.message}`);
                    },
                    onClose: () => {
                         if (get().status === 'processing') {
                            setStatus('success'); // Or 'idle' depending on desired final state
                        }
                    },
                });
            },

            approvePlan: async ({approved, feedback}) => {
                const {
                    currentRunId, sessionId, setStatus, addLog, addMessage,
                    setCode, setTestPlan, showToast,
                } = get();

                if (!currentRunId) {
                    showToast('Нет активного run_id для аппрува', 'error');
                    return;
                }
                
                // If rejecting, just send a normal API request, no stream needed
                if (!approved) {
                    try {
                        setStatus('idle');
                        addLog('System: Rejecting test plan...');
                        await fetch('/api/v1/chat/approve', {
                             method: 'POST',
                             headers: { 'Content-Type': 'application/json', 'X-Session-ID': sessionId },
                             body: JSON.stringify({ run_id: currentRunId, approved: false, feedback: feedback || null }),
                        });
                        showToast('План отклонён', 'info');
                        addMessage({
                            id: crypto.randomUUID(),
                            role: 'assistant',
                            content: 'План отклонён. Можете скорректировать запрос и отправить заново.',
                            timestamp: Date.now(),
                        });
                    } catch (e) {
                        setStatus('error');
                        addLog(`Error: ${(e as Error).message}`);
                    }
                    return;
                }
                
                // If approving, start a new stream
                setStatus('processing');
                addLog('System: Approving test plan and resuming workflow...');
                setCode('# Waiting for code generation after approval...');

                const handleStreamEvent = (data: StreamEvent) => {
                    // Same handler logic as in sendMessage
                     switch (data.type) {
                        case 'log':
                            addLog(data.content);
                            break;
                        case 'message':
                            addMessage({
                                id: crypto.randomUUID(),
                                role: 'assistant',
                                content: data.content,
                                timestamp: Date.now(),
                            });
                            break;
                        case 'code':
                            setCode(data.content);
                            break;
                        case 'plan':
                            setTestPlan(data.content);
                            break;
                        case 'status':
                             const newStatus = String(data.content || '').toUpperCase();
                            if (newStatus === 'COMPLETED') setStatus('success');
                            else if (newStatus === 'FAILED') setStatus('error');
                            else if (newStatus === 'WAITING_FOR_INPUT') setStatus('waiting_for_input');
                            else if (newStatus === 'WAITING_FOR_APPROVAL') setStatus('waiting_for_approval');
                            break;
                        case 'finish':
                            if (get().status !== 'waiting_for_input' && get().status !== 'waiting_for_approval') {
                                setStatus('success');
                                showToast('Код сгенерирован после аппрува', 'success');
                            }
                            break;
                        case 'error':
                             setStatus('error');
                             addLog(`Error: ${data.content}`);
                             break;
                    }
                };

                await chatStreamService.approvePlan({
                    runId: currentRunId,
                    sessionId,
                    approved: true,
                    feedback,
                }, {
                    onData: handleStreamEvent,
                    onError: (error) => {
                        setStatus('error');
                        addLog(`Error: ${error.message}`);
                    },
                    onClose: () => {
                        if (get().status === 'processing') {
                            setStatus('success');
                        }
                    },
                });
            },
            
            fetchAndShowDebugReport: async (runId: number) => {
                const { showToast, setStatus, sessionId, showDebugReport } = get();
                try {
                    setStatus('processing');
                    showToast('Fetching debug report...', 'info');
                    const response = await fetch(`/api/v1/execution/${runId}/debug-context`, {
                        headers: { 'X-Session-ID': sessionId },
                    });

                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.detail || 'Failed to fetch debug context');
                    }

                    const data: DebugContextResponse = await response.json();
                    showDebugReport(data);
                    showToast('Debug Report Loaded!', 'success');

                } catch (e: unknown) {
                    console.error('Failed to fetch debug report:', e);
                    showToast((e as Error).message, 'error');
                } finally {
                    setStatus('idle');
                }
            },
            
            clearWorkspace: async (hard = false) => {
                const { showToast, sessionId, clearChatState, setActiveEditorFile } = get();

                if (hard) {
                    try {
                        const response = await fetch(`/api/v1/chat/reset`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json', 'X-Session-ID': sessionId },
                        });
                        if (!response.ok) throw new Error('Failed to reset backend state');
                        showToast('Full workspace reset', 'success');
                    } catch (error) {
                        console.error('Failed to clear workspace:', error);
                        showToast(`Error during full reset: ${(error as Error).message}`, 'error');
                        return; // Don't clear frontend if backend fails
                    }
                }
                
                clearChatState();
                setActiveEditorFile('code');
            },
        }),
        {
            name: 'app-storage',
            partialize: (state) => ({
                sessionId: state.sessionId,
                selectedModel: state.selectedModel,
                editorSettings: state.editorSettings,
            }),
             onRehydrateStorage: () => (state) => {
                if (state && !state.sessionId) {
                    state.setSessionId(crypto.randomUUID());
                }
            }
        }
    )
);

// Export reusable types from slices
export * from './slices/chatSlice';
export * from './slices/uiSlice';
export * from './slices/settingsSlice';
