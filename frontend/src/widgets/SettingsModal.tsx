import {
	X,
	Server,
	Database,
	BrainCircuit,
	CheckCircle2,
	XCircle,
	RefreshCw,
	Loader2,
	Type,
	LayoutTemplate,
	Cpu,
	Sparkles,
	Box,
	Check,
	Key,
	Copy
} from 'lucide-react';
import {useState, useEffect} from 'react';
import {useAppStore, AVAILABLE_MODELS} from '../entities/store';

interface SettingsModalProps {
	isOpen: boolean;
	onClose: () => void;
}

interface SystemStatus {
	service: string;
	version: string;
	database: string;
	llm: string;
}

const TabButton = ({active, onClick, children}: {
	active: boolean,
	onClick: () => void,
	children: React.ReactNode
}) => (
	<button
		onClick={onClick}
		className={`px-4 py-3 text-xs font-bold uppercase tracking-wider transition-all relative ${active ? 'text-white' : 'text-muted hover:text-zinc-300'}`}
	>
		{children}
		{active &&
        <div className="absolute bottom-0 left-0 w-full h-0.5 bg-primary shadow-[0_-2px_10px_rgba(0,182,122,0.5)]"/>}
	</button>
);

const Toggle = ({value, onChange}: { value: boolean, onChange: (v: boolean) => void }) => (
	<button
		onClick={() => onChange(!value)}
		className={`w-10 h-5 rounded-full relative transition-colors duration-300 ${value ? 'bg-[#00b67a]' : 'bg-white/10'}`}
	>
		<div
			className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-transform duration-300 ${value ? 'left-6' : 'left-1'}`}/>
	</button>
);

export const SettingsModal = ({isOpen, onClose}: SettingsModalProps) => {
	const {
		editorSettings,
		updateEditorSettings,
		selectedModel,
		setSelectedModel,
		sessionId,
		setSessionId
	} = useAppStore();
	const [status, setStatus] = useState<SystemStatus | null>(null);
	const [loading, setLoading] = useState(false);
	const [activeTab, setActiveTab] = useState<'system' | 'model' | 'editor' | 'account'>('system');
	const [copied, setCopied] = useState(false);

	const checkHealth = async () => {
		setLoading(true);
		try {
			const API_URL = '/api/v1';
			const res = await fetch(`${API_URL}/health`);
			if (res.ok) {
				const data = await res.json();
				setStatus(data);
			}
		} catch (e) {
			console.error(e);
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		if (isOpen && activeTab === 'system') checkHealth();
	}, [isOpen, activeTab]);

	const handleCopySession = () => {
		navigator.clipboard.writeText(sessionId);
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	};

	if (!isOpen) return null;

	return (
		<div
			className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
			<div
				className="bg-[#1f2126] w-full max-w-2xl rounded-2xl border border-white/10 shadow-2xl p-0 relative overflow-hidden flex flex-col max-h-[85vh]">
				<div className="flex items-center justify-between px-6 border-b border-white/5 bg-[#18191d]/50">
					<div className="flex gap-2">
						<TabButton active={activeTab === 'system'} onClick={() => setActiveTab('system')}>System</TabButton>
						<TabButton active={activeTab === 'model'} onClick={() => setActiveTab('model')}>AI Models</TabButton>
						<TabButton active={activeTab === 'editor'} onClick={() => setActiveTab('editor')}>Editor</TabButton>
						<TabButton active={activeTab === 'account'} onClick={() => setActiveTab('account')}>Account</TabButton>
					</div>
					<button onClick={onClose} className="text-muted hover:text-white transition-colors p-2"><X size={20}/>
					</button>
				</div>

				<div className="p-0 overflow-y-auto custom-scrollbar">
					{activeTab === 'system' && (
						<div className="p-8 space-y-6">
							<div className="grid gap-4">
								<div className="flex items-center justify-between p-4 bg-[#18191d] rounded-xl border border-white/5">
									<div className="flex items-center gap-4">
										<div
											className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 border border-blue-500/20">
											<Server size={20}/>
										</div>
										<div>
											<div className="text-xs font-bold text-muted uppercase tracking-wider mb-0.5">Backend API</div>
											<div className="text-sm font-bold text-white">{status?.version || 'Unknown'}</div>
										</div>
									</div>
									{status ? <div
											className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-400 rounded-full text-xs font-medium border border-emerald-500/20">
											<CheckCircle2 size={14}/> Online</div>
										: <Loader2 size={18} className="animate-spin text-muted"/>}
								</div>

								<div className="flex items-center justify-between p-4 bg-[#18191d] rounded-xl border border-white/5">
									<div className="flex items-center gap-4">
										<div
											className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-400 border border-purple-500/20">
											<Database size={20}/>
										</div>
										<div>
											<div className="text-xs font-bold text-muted uppercase tracking-wider mb-0.5">Database</div>
											<div className="text-sm font-bold text-white capitalize">{status?.database || 'checking...'}</div>
										</div>
									</div>
									{status?.database === 'connected' ?
										<div
											className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-400 rounded-full text-xs font-medium border border-emerald-500/20">
											<CheckCircle2 size={14}/> Connected</div> :
										(loading ? <Loader2 size={18} className="animate-spin text-muted"/> :
											<XCircle size={18} className="text-error"/>)
									}
								</div>

								<div className="flex items-center justify-between p-4 bg-[#18191d] rounded-xl border border-white/5">
									<div className="flex items-center gap-4">
										<div
											className="w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center text-green-400 border border-green-500/20">
											<BrainCircuit size={20}/>
										</div>
										<div>
											<div className="text-xs font-bold text-muted uppercase tracking-wider mb-0.5">LLM Provider</div>
											<div className="text-sm font-bold text-white capitalize">{status?.llm || 'checking...'}</div>
										</div>
									</div>
									{status?.llm === 'ready' ?
										<div
											className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-400 rounded-full text-xs font-medium border border-emerald-500/20">
											<CheckCircle2 size={14}/> Ready</div> :
										(loading ? <Loader2 size={18} className="animate-spin text-muted"/> :
											<XCircle size={18} className="text-error"/>)
									}
								</div>
							</div>

							<button
								onClick={checkHealth}
								disabled={loading}
								className="w-full py-4 rounded-xl bg-[#00b67a] hover:bg-[#00a36d] text-white text-sm font-bold flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-emerald-900/20"
							>
								<RefreshCw size={16} className={loading ? "animate-spin" : ""}/>
								Refresh System Status
							</button>
						</div>
					)}

					{activeTab === 'model' && (
						<div className="p-6 space-y-3">
							<div className="grid grid-cols-1 gap-2">
								{AVAILABLE_MODELS.map(model => (
									<button
										key={model.id}
										onClick={() => setSelectedModel(model.id)}
										className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all text-left group relative overflow-hidden
                                            ${selectedModel === model.id
											? 'bg-[#00b67a]/10 border-[#00b67a] shadow-[0_0_20px_rgba(0,182,122,0.1)]'
											: 'bg-[#18191d] border-white/5 text-zinc-400 hover:bg-[#2b2d33] hover:border-white/10'}
                                        `}
									>
										{selectedModel === model.id && <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#00b67a]"/>}

										<div className="flex items-start gap-4">
											<div className={`mt-0.5 w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border
                                                ${selectedModel === model.id ? 'bg-[#00b67a]/20 text-[#00b67a] border-[#00b67a]/20' : 'bg-white/5 text-muted border-white/5 group-hover:text-white'}
                                            `}>
												{model.provider === 'Qwen' ? <Cpu size={20}/> :
													model.provider === 'Sber' ? <Sparkles size={20}/> : <Box size={20}/>}
											</div>
											<div>
												<div className="text-sm font-bold flex items-center gap-2 text-white">
													{model.name}
													{model.isFree && (
														<span
															className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400 uppercase tracking-wide border border-emerald-500/20">Free</span>
													)}
												</div>
												<div className="text-[11px] text-muted flex items-center gap-2 mt-1">
													<span className="px-2 py-0.5 rounded bg-white/5 flex items-center gap-1"><LayoutTemplate
														size={10}/> {model.context}</span>
													<span>{model.provider}</span>
												</div>
												{model.description && (
													<div className="text-[11px] text-zinc-500 mt-2">{model.description}</div>
												)}
											</div>
										</div>
										{selectedModel === model.id &&
                        <div className="w-6 h-6 rounded-full bg-[#00b67a] flex items-center justify-center text-white">
                            <Check size={14} strokeWidth={3}/></div>}
									</button>
								))}
							</div>
						</div>
					)}

					{activeTab === 'editor' && (
						<div className="p-8">
							<div className="grid gap-8">
								<div className="flex items-center justify-between">
									<div className="flex items-center gap-3">
										<div
											className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-zinc-400 border border-white/5">
											<Type size={20}/>
										</div>
										<div>
											<div className="text-sm font-bold text-white">Размер шрифта</div>
											<div className="text-xs text-muted">Размер текста в редакторе кода</div>
										</div>
									</div>
									<div className="flex bg-black/30 p-1 rounded-xl border border-white/5">
										{[12, 13, 14, 16, 18].map(size => (
											<button
												key={size}
												onClick={() => updateEditorSettings({fontSize: size})}
												className={`w-9 h-9 rounded-lg text-xs font-bold transition-all ${editorSettings.fontSize === size ? 'bg-[#2b2d33] text-white shadow-lg border border-white/10' : 'text-muted hover:text-white hover:bg-white/5'}`}
											>
												{size}
											</button>
										))}
									</div>
								</div>
								<div className="h-px bg-white/5"/>
								<div className="flex items-center justify-between">
									<div className="flex items-center gap-3">
										<div
											className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-zinc-400 border border-white/5">
											<LayoutTemplate size={20}/>
										</div>
										<div>
											<div className="text-sm font-bold text-white">Миникарта</div>
											<div className="text-xs text-muted">Показывать карту кода справа</div>
										</div>
									</div>
									<Toggle value={editorSettings.minimap} onChange={(v) => updateEditorSettings({minimap: v})}/>
								</div>
							</div>
						</div>
					)}

					{activeTab === 'account' && (
						<div className="p-8">
							<div className="p-6 bg-[#18191d] rounded-2xl border border-white/5">
								<div className="flex items-center gap-4 mb-6">
									<div
										className="w-12 h-12 rounded-xl bg-[#00b67a]/10 flex items-center justify-center text-[#00b67a] border border-[#00b67a]/20">
										<Key size={24}/>
									</div>
									<div>
										<h3 className="text-base font-bold text-white">Session Key Access</h3>
										<p className="text-xs text-muted">Используйте этот ключ для доступа к своей истории тестов с других
											устройств.</p>
									</div>
								</div>

								<div className="bg-black/30 p-4 rounded-xl border border-white/5">
									<label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block mb-2">Ваш
										уникальный ключ сессии (UUID)</label>
									<div className="flex gap-2">
										<input
											type="text"
											value={sessionId}
											onChange={(e) => setSessionId(e.target.value)}
											className="flex-1 bg-transparent text-sm font-mono text-white outline-none placeholder:text-zinc-700"
											placeholder="Paste your session UUID here..."
										/>
										<button
											onClick={handleCopySession}
											className="p-2 hover:bg-white/10 rounded-lg text-muted hover:text-white transition-colors"
											title="Copy Key"
										>
											{copied ? <Check size={16} className="text-emerald-400"/> : <Copy size={16}/>}
										</button>
									</div>
								</div>

								<div className="mt-4 flex gap-3 text-[11px] text-zinc-500">
									<p>⚠️ Храните этот ключ в безопасности. Любой, у кого он есть, может видеть вашу историю
										генераций.</p>
								</div>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
};
