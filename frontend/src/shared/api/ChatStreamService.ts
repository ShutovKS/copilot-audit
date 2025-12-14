const API_URL = '/api/v1';

export type StreamEvent = {
    type: 'meta' | 'log' | 'message' | 'code' | 'plan' | 'status' | 'finish' | 'error';
    content?: any;
    run_id?: number;
};

type StreamCallbacks = {
    onData: (event: StreamEvent) => void;
    onError: (error: Error) => void;
    onClose: () => void;
};

class ChatStreamService {
    private async processStream(
        response: Response,
        callbacks: StreamCallbacks
    ): Promise<void> {
        const reader = response.body?.getReader();
        if (!reader) {
            callbacks.onError(new Error('Failed to get stream reader.'));
            return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log('[SSE] Stream finished.');
                    callbacks.onClose();
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                const lines = buffer.split('\n\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const rawData = line.replace('data: ', '');
                            if (rawData.trim()) {
                                const data = JSON.parse(rawData) as StreamEvent;
                                callbacks.onData(data);
                            }
                        } catch (e) {
                            console.error('[SSE] Failed to parse JSON from line:', line, e);
                            // Don't throw, try to continue processing the stream
                        }
                    }
                }
            }
        } catch (e) {
            console.error('[SSE] An error occurred during stream processing:', e);
            callbacks.onError(e instanceof Error ? e : new Error('Unknown stream error'));
        }
    }

    async sendMessage(
        { message, modelName, runId, sessionId }: {
            message: string;
            modelName: string;
            runId: number | null;
            sessionId: string;
        },
        callbacks: StreamCallbacks
    ): Promise<void> {
        try {
            const response = await fetch(`${API_URL}/chat/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': sessionId,
                },
                body: JSON.stringify({
                    message: message,
                    model_name: modelName,
                    run_id: runId,
                }),
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            
            await this.processStream(response, callbacks);

        } catch (e) {
            callbacks.onError(e instanceof Error ? e : new Error('Failed to send message'));
        }
    }

    async approvePlan(
        { runId, sessionId, approved, feedback }: {
            runId: number;
            sessionId: string;
            approved: boolean;
            feedback?: string;
        },
        callbacks: StreamCallbacks
    ): Promise<void> {
         try {
            const response = await fetch(`${API_URL}/chat/approve`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': sessionId,
                },
                body: JSON.stringify({
                    run_id: runId,
                    approved: approved,
                    feedback: feedback || null,
                }),
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            
            // The approval endpoint also returns a stream for the subsequent steps
            await this.processStream(response, callbacks);

        } catch (e) {
            callbacks.onError(e instanceof Error ? e : new Error('Failed to approve plan'));
        }
    }
}

export const chatStreamService = new ChatStreamService();
