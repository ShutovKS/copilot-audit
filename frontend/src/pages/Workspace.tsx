import { Sidebar } from '../widgets/Sidebar';
import { CodeEditor } from '../widgets/Editor';
import { Terminal } from '../widgets/Terminal';

export const Workspace = () => {
  return (
    <div className="flex h-screen bg-[#131418] p-4 gap-4 overflow-hidden font-sans">
        {/* Left Block: Configuration (Input) */}
        <div className="w-[400px] flex-shrink-0 flex flex-col">
            <Sidebar />
        </div>

        {/* Center Block: Result (Editor) */}
        <div className="flex-1 flex flex-col min-w-0">
            <CodeEditor />
        </div>

        {/* Right Block: Status & Logs */}
        <div className="w-[340px] flex-shrink-0 flex flex-col">
            <Terminal />
        </div>
    </div>
  );
};
