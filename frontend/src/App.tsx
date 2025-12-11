import {Workspace} from "./pages/Workspace";
import {Toast} from "./widgets/Toast";
import {DebugReportModal} from "./widgets/DebugReportModal";

function App() {
	return (
		<div className="flex h-screen bg-slate-900 text-white">
			<Toast/>
			<DebugReportModal/>
			<main className="flex-1 flex flex-col h-screen">
				<Workspace/>
			</main>
		</div>
	);
}

export default App;
