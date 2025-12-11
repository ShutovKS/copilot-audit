import Editor from '@monaco-editor/react';
import {useAppStore} from '../entities/store';
import {Copy, Check, Loader2, Play, GitMerge, FileText, Code2, ExternalLink, X, Wrench} from 'lucide-react';
import {useState, useEffect, useRef} from 'react';
import {api, exportToGitLab} from '../shared/api/client';

export const CodeEditor = () => {
	const {code: storeCode, testPlan, editorSettings, addLog, status, currentRunId, sendMessage, setCode} = useAppStore();
	const [displayCode, setDisplayCode] = useState('');
	const [activeFile, setActiveFile] = useState<'code' | 'plan' | 'report'>('code');
	const [copied, setCopied] = useState(false);

	const [isRunning, setIsRunning] = useState(false);
	const [lastErrorLogs, setLastErrorLogs] = useState<string | null>(null);
	const [reportUrl, setReportUrl] = useState<string | null>(null);

	const [isModalOpen, setIsModalOpen] = useState(false);
	const [isExporting, setIsExporting] = useState(false);
	const [exportResult, setExportResult] = useState<{ url: string } | null>(null);
	const [projectId, setProjectId] = useState('');
	const [token, setToken] = useState('');
	const [gitlabUrl, setGitlabUrl] = useState('https://gitlab.com');

	const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
	const currentIndexRef = useRef(0);
	const targetCodeRef = useRef('');

	useEffect(() => {
		if (storeCode !== targetCodeRef.current) {
			const isAppend = storeCode.startsWith(targetCodeRef.current) && targetCodeRef.current !== '';

			if (!isAppend) {
				setDisplayCode(storeCode.length > 500 ? storeCode : '');
				currentIndexRef.current = storeCode.length > 500 ? storeCode.length : 0;
			}

			targetCodeRef.current = storeCode;

			if (!intervalRef.current && currentIndexRef.current < storeCode.length) {
				intervalRef.current = setInterval(() => {
					const target = targetCodeRef.current;
					const current = currentIndexRef.current;

					if (current < target.length) {
						const step = 25;
						setDisplayCode(target.slice(0, current + step));
						currentIndexRef.current += step;
					} else {
						setDisplayCode(target);
						if (intervalRef.current) {
							clearInterval(intervalRef.current);
							intervalRef.current = null;
						}
					}
				}, 10);
			}
		}
	}, [storeCode]);

	const handleCopy = () => {
		navigator.clipboard.writeText(activeFile === 'code' ? storeCode : testPlan);
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	};

	const handleRunTest = async () => {
		if (!storeCode || isRunning) return;

		if (!currentRunId) {
			addLog("Error: No active test run selected. Generate a test first.");
			return;
		}

		setIsRunning(true);
		setActiveFile('code');
		setLastErrorLogs(null);
		addLog("System: Initializing execution environment...");

		try {
			addLog(`System: Running pytest for Run ID ${currentRunId}...`);
			const res = await api.post(`/execution/${currentRunId}/run`);

			if (res.data.success) {
				addLog("System: Execution Successful!");
			} else {
				addLog("System: Execution Failed. Check logs.");
				if (res.data.logs) setLastErrorLogs(res.data.logs);
			}

			const logs = res.data.logs;
			if (logs && logs.trim()) {
				addLog(`Pytest Execution Log:${logs}`);
			}

			if (res.data.report_url) {
				const fullUrl = import.meta.env.VITE_API_URL.replace('/api/v1', '') + res.data.report_url;
				setReportUrl(fullUrl);
				setActiveFile('report');
				addLog(`System: Report generated: ${fullUrl}`);
			}

		} catch (e) {
			addLog(`Error: Execution failed - ${e}`);
		} finally {
			setIsRunning(false);
		}
	};

	const handleAutoFix = () => {
		if (!lastErrorLogs || !currentRunId) return;

		// Hide the "Auto-Fix" button immediately
		setLastErrorLogs(null);

		// Set a placeholder message in the editor
		setCode("# Fixing code... please wait...");

		// Construct the payload and send it via the centralized store action
		const fixPayload = `[AUTO-FIX] Failed Logs:${lastErrorLogs}`;
		sendMessage(fixPayload);
	};

	const handleExport = async () => {
		if (!projectId || !token) return;
		setIsExporting(true);
		try {
			const data = await exportToGitLab(storeCode, projectId, token, gitlabUrl);
			setExportResult({url: data.mr_url});
		} catch (e) {
			alert('Export failed: ' + e);
		} finally {
			setIsExporting(false);
		}
	};

	const isActionEnabled = (status === 'success' || currentRunId != null) && storeCode && !storeCode.startsWith('# Generated');

	return (
		<div
			className="bg-[#1f2126] rounded-2xl h-full flex flex-col overflow-hidden shadow-2xl border border-white/5 relative">
			<div className="h-12 flex items-center px-4 justify-between border-b border-white/5 bg-[#18191d]">
				<div className="flex gap-1 h-full pt-2">
					<button
						onClick={() => setActiveFile('code')}
						className={`flex items-center gap-2 px-4 rounded-t-lg text-xs font-medium transition-all ${activeFile === 'code' ? 'bg-[#1f2126] text-white border-t border-x border-white/5' : 'text-muted hover:text-white hover:bg-[#1f2126]/50'}`}
					>
						<Code2 size={14} className="text-blue-400"/> test_suite.py
					</button>
					<button
						onClick={() => setActiveFile('plan')}
						className={`flex items-center gap-2 px-4 rounded-t-lg text-xs font-medium transition-all ${activeFile === 'plan' ? 'bg-[#1f2126] text-white border-t border-x border-white/5' : 'text-muted hover:text-white hover:bg-[#1f2126]/50'}`}
					>
						<FileText size={14} className="text-yellow-400"/> test_plan.md
					</button>
					{reportUrl && (
						<button
							onClick={() => setActiveFile('report')}
							className={`flex items-center gap-2 px-4 rounded-t-lg text-xs font-medium transition-all ${activeFile === 'report' ? 'bg-[#1f2126] text-white border-t border-x border-white/5' : 'text-muted hover:text-white hover:bg-[#1f2126]/50'}`}
						>
							<ExternalLink size={14} className="text-primary"/> Allure Report
						</button>
					)}
				</div>

				<div className="flex items-center gap-2 mb-1">
					<button
						onClick={handleCopy}
						className="p-1.5 hover:bg-[#2b2d33] rounded-md text-muted hover:text-white transition-colors"
						title="Copy Code"
					>
						{copied ? <Check size={14} className="text-success"/> : <Copy size={14}/>}
					</button>

					<button
						onClick={() => setIsModalOpen(true)}
						disabled={!isActionEnabled}
						className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-[10px] font-bold transition-all border
                        ${!isActionEnabled
							? 'bg-[#2b2d33] text-zinc-600 border-white/5 cursor-not-allowed'
							: 'bg-secondary/10 hover:bg-secondary/20 text-secondary hover:text-white border-secondary/20'
						}
                    `}
					>
						<GitMerge size={12}/> Export
					</button>

					<button
						onClick={handleRunTest}
						disabled={isRunning || !isActionEnabled}
						className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-[10px] font-bold transition-all border
                        ${isRunning || !isActionEnabled
							? 'bg-[#2b2d33] text-zinc-600 border-white/5 cursor-not-allowed'
							: 'bg-[#00b67a] hover:bg-[#00a36d] text-white border-transparent hover:shadow-[0_0_15px_rgba(0,182,122,0.4)] hover:scale-[1.02] active:scale-[0.98]'
						}
                    `}
					>
						{isRunning ? <Loader2 size={12} className="animate-spin"/> : <Play size={12} fill="currentColor"/>}
						Run Test
					</button>
				</div>
			</div>

			<div className="flex-1 flex min-h-0 relative">
				{activeFile === 'report' && reportUrl ? (
					<iframe src={reportUrl} className="w-full h-full bg-white" title="Allure Report"/>
				) : (
					<div className="flex-1 bg-[#1f2126] relative">
						<Editor
							height="100%"
							defaultLanguage={activeFile === 'code' ? 'python' : 'markdown'}
							theme="vs-dark"
							value={activeFile === 'code' ? displayCode : (testPlan || '*Test plan not generated yet*')}
							options={{
								readOnly: true,
								minimap: {enabled: editorSettings.minimap},
								fontSize: editorSettings.fontSize,
								wordWrap: editorSettings.wordWrap,
								fontFamily: 'JetBrains Mono, monospace',
								padding: {top: 20, bottom: 20},
							}}
							onMount={(_editor, monaco) => {
								monaco.editor.defineTheme('cloud-rounded', {
									base: 'vs-dark',
									inherit: true,
									rules: [],
									colors: {
										'editor.background': '#1f2126',
										'editor.lineHighlightBackground': '#2b2d33'
									}
								});
								monaco.editor.setTheme('cloud-rounded');
							}}
						/>

						{/* Auto-Fix Overlay */}
						{lastErrorLogs && activeFile === 'code' && (
							<div className="absolute bottom-6 right-6 z-10 animate-in slide-in-from-bottom-4">
								<button
									onClick={handleAutoFix}
									className="flex items-center gap-2 px-4 py-3 bg-error hover:bg-red-600 text-white rounded-xl shadow-lg font-bold transition-all hover:scale-105"
								>
									<Wrench size={18}/> Auto-Fix with AI
								</button>
							</div>
						)}
					</div>
				)}
			</div>

			{isModalOpen && (
				<div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
					<div className="bg-[#1f2126] w-full max-w-md rounded-2xl border border-white/10 shadow-2xl p-6">
						{/* Export Modal Content (Same as before) */}
						<div className="flex justify-between items-center mb-6">
							<div className="flex items-center gap-2">
								<GitMerge className="text-secondary"/>
								<h3 className="text-lg font-bold text-white">Export to GitLab</h3>
							</div>
							<button onClick={() => setIsModalOpen(false)} className="text-muted hover:text-white"><X size={20}/>
							</button>
						</div>

						{!exportResult ? (
							<div className="space-y-4">
								<div>
									<label className="block text-xs font-bold text-muted uppercase mb-1">Project ID</label>
									<input type="text"
									       className="w-full bg-[#18191d] border border-white/10 rounded-lg p-3 text-sm text-white focus:border-secondary outline-none transition-colors"
									       placeholder="e.g. 54321" value={projectId} onChange={e => setProjectId(e.target.value)}/>
								</div>
								<div>
									<label className="block text-xs font-bold text-muted uppercase mb-1">Access Token</label>
									<input type="password"
									       className="w-full bg-[#18191d] border border-white/10 rounded-lg p-3 text-sm text-white focus:border-secondary outline-none transition-colors"
									       placeholder="glpat-..." value={token} onChange={e => setToken(e.target.value)}/>
								</div>
								<div>
									<label className="block text-xs font-bold text-muted uppercase mb-1">GitLab URL</label>
									<input type="text"
									       className="w-full bg-[#18191d] border border-white/10 rounded-lg p-3 text-sm text-white focus:border-secondary outline-none transition-colors"
									       value={gitlabUrl} onChange={e => setGitlabUrl(e.target.value)}/>
								</div>

								<button
									onClick={handleExport}
									disabled={isExporting}
									className="w-full py-3 bg-secondary hover:bg-secondary/80 text-white rounded-xl font-bold flex items-center justify-center gap-2 mt-4 transition-colors"
								>
									{isExporting ? <Loader2 className="animate-spin"/> : 'Create Merge Request'}
								</button>
							</div>
						) : (
							<div className="text-center space-y-4">
								<div className="w-12 h-12 bg-success/20 rounded-full flex items-center justify-center mx-auto">
									<Check size={24} className="text-success"/>
								</div>
								<h4 className="text-white font-bold">Merge Request Created!</h4>
								<a href={exportResult.url} target="_blank" rel="noreferrer"
								   className="block p-3 bg-[#18191d] rounded-lg text-primary text-sm underline truncate hover:text-white transition-colors">
									{exportResult.url}
								</a>
								<button onClick={() => {
									setIsModalOpen(false);
									setExportResult(null);
								}} className="text-sm text-muted hover:text-white">
									Close
								</button>
							</div>
						)}
					</div>
				</div>
			)}
		</div>
	);
};
