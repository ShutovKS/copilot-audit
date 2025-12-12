import {CheckCircle2, FileText, PencilLine, X} from 'lucide-react';
import {useEffect, useMemo, useState} from 'react';
import {useAppStore} from '../entities/store';

export const ApprovalModal = () => {
	const {status, testPlan, approvePlan, showToast} = useAppStore();
	const isOpen = status === 'waiting_for_approval';

	const initialText = useMemo(() => testPlan || '', [testPlan]);
	const [editedPlan, setEditedPlan] = useState(initialText);

	useEffect(() => {
		if (isOpen) setEditedPlan(initialText);
	}, [isOpen, initialText]);

	if (!isOpen) return null;

	const canApprove = editedPlan.trim().length > 0;

	return (
		<div className="absolute inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-6 animate-in fade-in duration-200">
			<div className="bg-[#1f2126] w-full max-w-3xl rounded-2xl border border-white/10 shadow-2xl p-0 overflow-hidden">
				<div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-[#18191d]/50">
					<div className="flex items-center gap-3">
						<div className="w-10 h-10 rounded-xl bg-yellow-500/10 flex items-center justify-center text-yellow-400 border border-yellow-500/20">
							<FileText size={18}/>
						</div>
						<div>
							<div className="text-xs font-bold text-muted uppercase tracking-wider">Human-in-the-Loop</div>
							<div className="text-sm font-bold text-white">Подтвердите план тестирования</div>
						</div>
					</div>
					<button
						onClick={() => {
							showToast('Пожалуйста, выберите: Approve или Reject', 'info');
						}}
						className="text-muted hover:text-white transition-colors p-2"
						title="Close"
					>
						<X size={18}/>
					</button>
				</div>

				<div className="p-6 space-y-4">
					<div className="flex items-start gap-3 p-4 rounded-xl bg-[#18191d] border border-white/5">
						<PencilLine size={16} className="text-zinc-400 mt-0.5"/>
						<div>
							<div className="text-xs font-bold text-white">Можно отредактировать план перед генерацией кода</div>
							<div className="text-[11px] text-muted mt-1">
								После аппрува граф продолжит выполнение и перейдёт к генерации кода.
							</div>
						</div>
					</div>

					<textarea
						value={editedPlan}
						onChange={(e) => setEditedPlan(e.target.value)}
						rows={14}
						className="w-full bg-[#18191d] border border-white/10 rounded-xl p-4 text-[12px] text-zinc-200 focus:border-primary/50 focus:ring-0 resize-none placeholder:text-zinc-600 custom-scrollbar outline-none font-mono whitespace-pre-wrap"
						placeholder="План тестирования..."
					/>

					<div className="flex gap-3">
						<button
							onClick={() => approvePlan({approved: false, feedback: editedPlan})}
							className="flex-1 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-sm font-medium text-zinc-300 transition-colors"
						>
							Reject
						</button>
						<button
							onClick={() => approvePlan({approved: true, feedback: editedPlan})}
							disabled={!canApprove}
							className="flex-1 py-3 rounded-xl bg-[#00b67a] hover:bg-[#00a36d] text-sm font-bold text-white flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:bg-zinc-700"
						>
							<CheckCircle2 size={16}/> Approve & Generate Code
						</button>
					</div>
				</div>
			</div>
		</div>
	);
};
