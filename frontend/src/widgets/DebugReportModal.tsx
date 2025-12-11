import {useAppStore} from "../entities/store";
import {X, FileCode, ServerCrash, Terminal, Workflow} from "lucide-react";
import Editor from '@monaco-editor/react';
import {useState, type ReactNode} from "react";

interface SectionProps {
	title: string;
	icon: ReactNode;
	children: ReactNode;
	defaultOpen?: boolean;
}

const Section = ({title, icon, children, defaultOpen = false}: SectionProps) => {
	const [isOpen, setIsOpen] = useState(defaultOpen);
	return (
		<div className="border border-slate-700 rounded-lg mb-4">
			<button
				className="w-full flex justify-between items-center p-3 bg-slate-800 rounded-t-lg"
				onClick={() => setIsOpen(!isOpen)}
			>
				<div className="flex items-center">
					{icon}
					<h3 className="text-lg font-semibold ml-2">{title}</h3>
				</div>
				<span className={`transform transition-transform ${isOpen ? 'rotate-180' : ''}`}>▼</span>
			</button>
			{isOpen && <div className="p-4 bg-slate-900 rounded-b-lg">{children}</div>}
		</div>
	);
};


export function DebugReportModal() {
	const {isDebugReportOpen, debugContext, hideDebugReport} = useAppStore();

	if (!isDebugReportOpen || !debugContext) {
		return null;
	}

	return (
		<div className="fixed inset-0 bg-black bg-opacity-60 z-40 flex items-center justify-center p-4">
			<div className="bg-slate-800 text-white rounded-lg shadow-2xl w-full max-w-4xl h-[90vh] flex flex-col">
				{/* Header */}
				<div className="flex justify-between items-center p-4 border-b border-slate-700">
					<h2 className="text-2xl font-bold text-cyan-400">Auto-Fix Debug Report</h2>
					<button onClick={hideDebugReport} className="text-slate-400 hover:text-white">
						<X size={28}/>
					</button>
				</div>

				{/* Content */}
				<div className="p-6 overflow-y-auto">
					<Section title="Agent's Hypothesis" icon={<Workflow className="text-cyan-400"/>} defaultOpen={true}>
						<p className="text-lg italic text-slate-300">
							{debugContext.hypothesis || "The agent did not provide a specific hypothesis."}
						</p>
					</Section>

					<Section title="Original Error Log" icon={<ServerCrash className="text-red-400"/>}>
                        <pre className="bg-slate-950 p-3 rounded-md text-sm text-red-300 whitespace-pre-wrap font-mono">
                            {debugContext.original_error}
                        </pre>
					</Section>

					<Section title="DOM Snapshot at Failure" icon={<FileCode className="text-blue-400"/>}>
						<div className="h-96 w-full border border-slate-600 rounded-md">
							<Editor
								language="html"
								value={debugContext.dom_snapshot}
								options={{
									readOnly: true,
									minimap: {enabled: false},
									fontSize: 13,
									wordWrap: 'on',
									fontFamily: 'JetBrains Mono, monospace',
									padding: {top: 10, bottom: 10},
								}}
							/>
						</div>
					</Section>

					{debugContext.network_errors?.length > 0 && (
						<Section title="Network Errors" icon={<Terminal className="text-yellow-400"/>}>
                            <pre
	                            className="bg-slate-950 p-3 rounded-md text-sm text-yellow-300 whitespace-pre-wrap font-mono">
                                {debugContext.network_errors.join('\n')}
                            </pre>
						</Section>
					)}

					{debugContext.console_logs?.length > 0 && (
						<Section title="Console Logs" icon={<Terminal className="text-purple-400"/>}>
                             <pre
	                             className="bg-slate-950 p-3 rounded-md text-sm text-purple-300 whitespace-pre-wrap font-mono">
                                {debugContext.console_logs.join('\n')}
                            </pre>
						</Section>
					)}
				</div>
			</div>
		</div>
	);
}
