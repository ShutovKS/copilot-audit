import {useEffect} from 'react';
import {CheckCircle2, XCircle, Info, X} from 'lucide-react';
import {useAppStore} from '../entities/store';

export const Toast = () => {
	const {toast, hideToast} = useAppStore();

	useEffect(() => {
		if (toast) {
			const timer = setTimeout(hideToast, 5000);
			return () => clearTimeout(timer);
		}
	}, [toast, hideToast]);

	if (!toast) return null;

	return (
		<div className="fixed top-6 right-6 z-[100] animate-in slide-in-from-top-2 fade-in duration-300">
			<div className={`flex items-start gap-3 p-4 rounded-xl shadow-2xl border min-w-[300px] max-w-md backdrop-blur-md
                ${toast.type === 'error' ? 'bg-red-950/90 border-red-500/20 text-red-100' :
				toast.type === 'success' ? 'bg-[#1f2126]/90 border-primary/20 text-white' :
					'bg-blue-950/90 border-blue-500/20 text-blue-100'}
            `}>
				<div className={`mt-0.5 ${
					toast.type === 'error' ? 'text-red-400' :
						toast.type === 'success' ? 'text-primary' :
							'text-blue-400'
				}`}>
					{toast.type === 'error' ? <XCircle size={18}/> :
						toast.type === 'success' ? <CheckCircle2 size={18}/> :
							<Info size={18}/>}
				</div>

				<div className="flex-1 text-xs font-medium leading-relaxed whitespace-pre-wrap">
					{toast.message}
				</div>

				<button onClick={hideToast} className="text-white/50 hover:text-white transition-colors">
					<X size={14}/>
				</button>
			</div>
		</div>
	);
};
