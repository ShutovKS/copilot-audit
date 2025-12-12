import {create} from 'zustand';
import {persist} from 'zustand/middleware';

export type GenerationStatus = 'idle' | 'processing' | 'success' | 'error' | 'waiting_for_input' | 'waiting_for_approval';
export type EditorFile = 'code' | 'plan' | 'report';

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
	setMessages: (msgs: ChatMessage[]) => void;
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

	// New action for handling SSE
	sendMessage: (message: string) => Promise<void>;
	approvePlan: (params: { approved: boolean; feedback?: string }) => Promise<void>;

	// State for Debug Report
	debugContext: DebugContextResponse | null;
	isDebugReportOpen: boolean;
	fetchAndShowDebugReport: (runId: number) => Promise<void>;
	hideDebugReport: () => void;

	clearWorkspace: () => void;

	reportUrl: string | null;
	setReportUrl: (url: string | null) => void;

	activeEditorFile: EditorFile;
	setActiveEditorFile: (file: EditorFile) => void;
}

export interface DebugContextResponse {
	summary: string;
	original_error: string;
	dom_snapshot: string;
	network_errors: string[];
	console_logs: string[];
	hypothesis: string | null;
}


export const useAppStore = create<AppState>()(
	persist(
		(set, get) => ({
			sessionId: crypto.randomUUID(),
			setSessionId: (sessionId) => set({sessionId}),

			currentRunId: null,
			setCurrentRunId: (currentRunId) => set({currentRunId}),

			messages: [],
			addMessage: (msg) => set((state) => ({messages: [...state.messages, msg]})),
			setMessages: (msgs) => set({messages: msgs}),
			clearMessages: () => set({messages: []}),

			input: '',
			setInput: (val) => set((state) => ({
				input: typeof val === 'function' ? val(state.input) : val
			})),

			code: '# Generated tests will appear here...',
			setCode: (code) => set({code}),

			testPlan: '',
			setTestPlan: (testPlan) => set({testPlan}),

			logs: [],
			addLog: (content) => {
				let type: LogEntry['type'] = 'info';
				// Fix: Don't flag 'Failed' in test names (e.g. TestFailedLogin) as errors. Use strict Pytest 'FAILED' status.
    if (content.includes('Error:') || content.includes('Execution Failed') || content.includes('FAILED')) type = 'error';
				else if (content.includes('Success') || content.includes('Valid')) type = 'success';
				else if (content.includes('Analyst') || content.includes('Coder')) type = 'debug';

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

				set((state) => ({logs: [...state.logs, newLog]}));
			},
			clearLogs: () => set({logs: [], testPlan: ''}),

			status: 'idle',
			setStatus: (status) => set({status}),

			error: null,
			setError: (error) => set({error}),

			editorSettings: {
				fontSize: 13,
				minimap: false,
				wordWrap: 'on'
			},
			updateEditorSettings: (newSettings) => set((state) => ({
				editorSettings: {...state.editorSettings, ...newSettings}
			})),

			selectedModel: DEFAULT_MODEL,
			setSelectedModel: (selectedModel) => set({selectedModel}),

			toast: null,
			showToast: (message, type) => set({toast: {message, type}}),
			hideToast: () => set({toast: null}),

			clearWorkspace: async (hard = false) => {
				const { showToast, sessionId } = get();

				if (hard) {
					try {
						const API_URL = '/api/v1';
						const response = await fetch(`${API_URL}/chat/reset`, {
							method: 'POST',
							headers: {
								'Content-Type': 'application/json',
								'X-Session-ID': sessionId,
							},
						});

						if (!response.ok) {
							throw new Error('Failed to reset backend state');
						}
						showToast('Full workspace reset', 'success');
					} catch (error) {
						console.error('Failed to clear workspace:', error);
						showToast(`Error during full reset: ${(error as Error).message}`, 'error');
						// Do not proceed with frontend reset if backend fails
						return;
					}
				}

				set({
					messages: [],
					logs: [],
					code: '# Generated tests will appear here...',
					testPlan: '',
					status: 'idle',
					error: null,
					currentRunId: null,
					reportUrl: null,
					activeEditorFile: 'code',
				});

				if (!hard) {
					// showToast('Workspace cleared', 'info');
				}
			},

			reportUrl: null,
			setReportUrl: (url) => set({reportUrl: url}),

			activeEditorFile: 'code',
			setActiveEditorFile: (file) => set({activeEditorFile: file}),

			// Centralized SSE Logic
			sendMessage: async (message: string) => {
				const {
					addMessage,
					setStatus,
					clearLogs,
					addLog,
					setCurrentRunId,
					setCode,
					setTestPlan,
					showToast,
					currentRunId,
					selectedModel,
					sessionId
				} = get();

				addMessage({
					id: crypto.randomUUID(),
					role: 'user',
					content: message,
					timestamp: Date.now()
				});

				setStatus('processing');
				if (!currentRunId) clearLogs();

				addLog(`System: Sending message to Chat Agent...`);
				console.log('[SSE] Initiating new message stream...');

				const API_URL = '/api/v1';
				try {
					const response = await fetch(`${API_URL}/chat/message`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							'X-Session-ID': sessionId
						},
						body: JSON.stringify({
							message: message,
							model_name: selectedModel,
							run_id: currentRunId
						})
					});
					if (!response.ok) throw new Error(`API Error: ${response.statusText}`);

					const reader = response.body?.getReader();
					const decoder = new TextDecoder();
					let buffer = '';

					if (reader) {
						console.log('[SSE] Reader obtained, starting stream processing loop.');
						while (true) {
							const {done, value} = await reader.read();

							if (done) {
								console.log('[SSE] Stream finished (reader signaled "done").');
								break;
							}

							const chunk = decoder.decode(value, {stream: true});
							console.log('[SSE] Received raw chunk:', chunk);
							buffer += chunk;

							const lines = buffer.split('\n\n');
							buffer = lines.pop() || '';

							for (const line of lines) {
								if (line.startsWith('data: ')) {
									try {
										const rawData = line.replace('data: ', '');
										if (rawData.trim()) {
											const data = JSON.parse(rawData);
											console.log('[SSE] Parsed data event:', data);

											if (data.type === 'meta') {
												console.log('[SSE] Handling "meta" event. Run ID:', data.run_id);
												if (data.run_id) setCurrentRunId(data.run_id);
											}
											if (data.type === 'log') {
												console.log('[SSE] Handling "log" event.');
												addLog(data.content);
											}
											if (data.type === 'message') {
												console.log('[SSE] Handling "message" event.');
												addMessage({
													id: crypto.randomUUID(),
													role: 'assistant',
													content: data.content,
													timestamp: Date.now()
												});
											}
											if (data.type === 'code') {
												console.log('[SSE] Handling "code" event.');
												setCode(data.content);
											}
											if (data.type === 'plan') {
												console.log('[SSE] Handling "plan" event.');
												setTestPlan(data.content);
											}
											if (data.type === 'status') {
												const raw = String(data.content || '');
												const normalized = raw.toUpperCase();
												console.log('[SSE] Handling "status" event:', raw);
												if (normalized === 'COMPLETED') setStatus('success');
												else if (normalized === 'FAILED') setStatus('error');
												else if (normalized === 'WAITING_FOR_INPUT') setStatus('waiting_for_input');
												else if (normalized === 'WAITING_FOR_APPROVAL') setStatus('waiting_for_approval');
											}
											if (data.type === 'finish') {
												console.log('[SSE] Handling "finish" event.');
												const finalStatus = get().status;
												if (finalStatus !== 'waiting_for_input' && finalStatus !== 'waiting_for_approval') {
													setStatus('success');
													showToast("Code Updated Successfully!", 'success');
													addMessage({
														id: crypto.randomUUID(),
														role: 'assistant',
														content: 'Готово! Я обновил код и план тестирования.',
														timestamp: Date.now()
													});
												} else {
													// Keep the waiting status so the UI can request input/approval.
												}
											}
											if (data.type === 'error') {
												console.log('[SSE] Handling "error" event.');
												setStatus('error');
												addLog(`Error: ${data.content}`);
												addMessage({
													id: crypto.randomUUID(),
													role: 'assistant',
													content: `Ошибка: ${data.content}`,
													timestamp: Date.now()
												});
											}
										}
									} catch (e) {
										console.error('[SSE] Failed to parse JSON from line:', line, e);
									}
								}
							}
						}
					}
					console.log('[SSE] Stream processing loop has finished.');
				} catch (e: unknown) {
					setStatus('error');
					addLog(`Error: ${(e as Error).message}`);
					console.error('[SSE] An error occurred in the fetch or stream handling:', e);
				} finally {
					if (get().status === 'processing') {
						console.warn('[SSE] Finally block: Status was still "processing". Forcing to "error" as a safety measure.');
						setStatus('error');
						addMessage({
							id: crypto.randomUUID(),
							role: 'assistant',
							content: 'Произошла непредвиденная ошибка при обработке ответа.',
							timestamp: Date.now()
						});
					}
				}
			},

			approvePlan: async ({ approved, feedback }: { approved: boolean; feedback?: string }) => {
				const {
					currentRunId,
					sessionId,
					setStatus,
					addLog,
					addMessage,
					setCode,
					setTestPlan,
					showToast,
				} = get();

				if (!currentRunId) {
					showToast('Нет активного run_id для аппрува', 'error');
					return;
				}

				if (!approved) {
					try {
						setStatus('processing');
						addLog('System: Rejecting test plan...');
						const API_URL = '/api/v1';
						const res = await fetch(`${API_URL}/chat/approve`, {
							method: 'POST',
							headers: {
								'Content-Type': 'application/json',
								'X-Session-ID': sessionId,
							},
							body: JSON.stringify({ run_id: currentRunId, approved: false, feedback: feedback || null }),
						});
						if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
						showToast('План отклонён', 'info');
						setStatus('idle');
						addMessage({
							id: crypto.randomUUID(),
							role: 'assistant',
							content: 'План отклонён. Можете скорректировать запрос и отправить заново.',
							timestamp: Date.now(),
						});
					} catch (e: unknown) {
						setStatus('error');
						addLog(`Error: ${(e as Error).message}`);
					}
					return;
				}

				// Approve: resume SSE
				setStatus('processing');
				addLog('System: Approving test plan and resuming workflow...');
				setCode('# Waiting for code generation after approval...');

				const API_URL = '/api/v1';
				try {
					const response = await fetch(`${API_URL}/chat/approve`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							'X-Session-ID': sessionId,
						},
						body: JSON.stringify({ run_id: currentRunId, approved: true, feedback: feedback || null }),
					});
					if (!response.ok) throw new Error(`API Error: ${response.statusText}`);

					const reader = response.body?.getReader();
					const decoder = new TextDecoder();
					let buffer = '';

					if (reader) {
						while (true) {
							const { done, value } = await reader.read();
							if (done) break;
							buffer += decoder.decode(value, { stream: true });
							const lines = buffer.split('\n\n');
							buffer = lines.pop() || '';

							for (const line of lines) {
								if (!line.startsWith('data: ')) continue;
								const rawData = line.replace('data: ', '');
								if (!rawData.trim()) continue;

								try {
									const data = JSON.parse(rawData);
									if (data.type === 'log') addLog(data.content);
									if (data.type === 'message') {
										addMessage({
											id: crypto.randomUUID(),
											role: 'assistant',
											content: data.content,
											timestamp: Date.now(),
										});
									}
									if (data.type === 'code') setCode(data.content);
									if (data.type === 'plan') setTestPlan(data.content);
									if (data.type === 'status') {
										const raw = String(data.content || '');
										const normalized = raw.toUpperCase();
										if (normalized === 'COMPLETED') setStatus('success');
										else if (normalized === 'FAILED') setStatus('error');
										else if (normalized === 'WAITING_FOR_INPUT') setStatus('waiting_for_input');
										else if (normalized === 'WAITING_FOR_APPROVAL') setStatus('waiting_for_approval');
									}
									if (data.type === 'finish') {
										const finalStatus = get().status;
										if (finalStatus !== 'waiting_for_input' && finalStatus !== 'waiting_for_approval') {
											setStatus('success');
											showToast('Код сгенерирован после аппрува', 'success');
										}
									}
								} catch (e) {
									console.error('[SSE] Failed to parse approval JSON:', line, e);
								}
							}
						}
					}
				} catch (e: unknown) {
					setStatus('error');
					addLog(`Error: ${(e as Error).message}`);
				}
			},

			// Debug Report State and Actions
			debugContext: null,
			isDebugReportOpen: false,
			hideDebugReport: () => set({isDebugReportOpen: false, debugContext: null}),
			fetchAndShowDebugReport: async (runId: number) => {
				const {showToast, setStatus, sessionId} = get();
				try {
					setStatus('processing');
					showToast('Fetching debug report...', 'info');
					const API_URL = '/api/v1';
					const response = await fetch(`${API_URL}/execution/${runId}/debug-context`, {
						headers: {
							'X-Session-ID': sessionId
						}
					});

					if (!response.ok) {
						const err = await response.json();
						throw new Error(err.detail || 'Failed to fetch debug context');
					}

					const data: DebugContextResponse = await response.json();
					set({debugContext: data, isDebugReportOpen: true});
					showToast('Debug Report Loaded!', 'success');

				} catch (e: unknown) {
					console.error('Failed to fetch debug report:', e);
					showToast((e as Error).message, 'error');
				} finally {
					setStatus('idle');
				}
			}
		}),
		{
			name: 'app-storage',
			partialize: (state) => ({
				editorSettings: state.editorSettings,
				selectedModel: state.selectedModel,
				sessionId: state.sessionId,
			}),
			onRehydrateStorage: () => (state) => {
				if (state && !state.sessionId) state.setSessionId(crypto.randomUUID());
			}
		}
	)
);
