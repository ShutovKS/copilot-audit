import json
import logging
import zipfile
from pathlib import Path
from typing import Any

from src.app.core.config import get_settings

logger = logging.getLogger(__name__)


class TraceInspector:
	def __init__(self):
		self.settings = get_settings()

	def _find_trace_file(self, run_id: int) -> Path | None:
		"""Finds the trace.zip file in the run's allure-results directory."""
		run_dir = self.settings.TEMP_DIR / str(run_id)
		results_dir = run_dir / "allure-results"
		if not results_dir.exists():
			logger.warning(f"TraceInspector: Allure results directory not found for run {run_id}")
			return None

		for f in results_dir.glob("*.zip"):
			if f.name.endswith("-trace.zip"):
				logger.info(f"TraceInspector: Found trace file: {f.name}")
				return f

		logger.warning(f"TraceInspector: No trace file found in {results_dir}")
		return None

	def _extract_trace_data(self, trace_file: Path) -> dict[str, Any]:
		"""Extracts all JSON sources from the trace.zip into a dictionary."""
		data = {}
		try:
			with zipfile.ZipFile(trace_file, 'r') as z:
				for filename in z.namelist():
					if filename.endswith('.json'):
						with z.open(filename) as f:
							# Use filename as key, e.g., 'trace.json', 'network.json'
							data[filename.split('/')[-1]] = json.load(f)
		except (zipfile.BadZipFile, json.JSONDecodeError) as e:
			logger.error(f"TraceInspector: Failed to parse trace file {trace_file}. Error: {e}")
		return data

	def _get_failed_action(self, trace_data: dict[str, Any]) -> dict | None:
		"""Finds the last action that has an error."""
		trace_json = trace_data.get("trace.json", {})
		actions = trace_json.get("actions", [])
		for action in reversed(actions):
			if action.get("error"):
				return action
		return None

	def _get_dom_snapshot(self, failed_action: dict, trace_data: dict[str, Any]) -> str:
		"""Gets the DOM snapshot after the failed action."""
		if not failed_action or "after" not in failed_action.get("metadata", {}):
			return "No DOM snapshot available for the failed action."

		snapshot_id = failed_action["metadata"]["after"]
		snapshot_file = f"snapshot_{snapshot_id.split('@')[-1]}.json"

		dom_data = trace_data.get(snapshot_file, {})
		# The actual DOM content is usually in the first element of the list
		return json.dumps(dom_data[0] if isinstance(dom_data, list) and dom_data else dom_data, indent=2)

	def _get_network_errors(self, trace_data: dict[str, Any]) -> list[str]:
		"""Gets all network requests that resulted in an error."""
		network_json = trace_data.get("network.json", {})
		errors = []
		for request in network_json.get("requests", []):
			if 400 <= request.get("status", 200) < 600:
				errors.append(
					f"URL: {request.get('url')}, Method: {request.get('method')}, Status: {request.get('status')}"
				)
		return errors

	def _get_console_logs(self, trace_data: dict[str, Any]) -> list[str]:
		"""Gets all console error/warning messages."""
		console_json = trace_data.get("console.json", {})
		logs = []
		for msg in console_json.get("messages", []):
			if msg.get("type").lower() in ["error", "warning"]:
				logs.append(f"Type: {msg.get('type')}, Text: {msg.get('text')}")
		return logs

	def get_failure_context(self, run_id: int, original_error: str) -> dict[str, Any] | None:
		"""
		Main entry point. Finds the trace file for a run, parses it,
		and returns a structured context of the failure.
		"""
		trace_file = self._find_trace_file(run_id)
		if not trace_file:
			return None

		trace_data = self._extract_trace_data(trace_file)
		if not trace_data:
			return None

		failed_action = self._get_failed_action(trace_data)
		if not failed_action:
			logger.warning(f"TraceInspector: No failed action with an error found in trace for run {run_id}.")
			return {
				"summary": "Could not pinpoint a specific failed action in the trace, but context is available.",
				"original_error": original_error,
				"network_errors": self._get_network_errors(trace_data),
				"console_logs": self._get_console_logs(trace_data),
				"dom_snapshot": "Could not be retrieved as the specific failed action was not identified."
			}

		action_summary = f"Failed Action: {failed_action.get('name')} with selector '{failed_action.get('selector')}'"

		dom_snapshot = self._get_dom_snapshot(failed_action, trace_data)
		network_errors = self._get_network_errors(trace_data)
		console_logs = self._get_console_logs(trace_data)

		return {
			"summary": action_summary,
			"original_error": original_error,
			"dom_snapshot": dom_snapshot,
			"network_errors": network_errors,
			"console_logs": console_logs,
		}
