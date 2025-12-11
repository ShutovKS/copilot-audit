import logging
import os
import subprocess
from pathlib import Path

from src.app.core.config import get_settings

logger = logging.getLogger(__name__)


class CodebaseNavigator:
	"""A service for cloning and inspecting local git repositories."""

	def __init__(self):
		self.settings = get_settings()
		self.clone_dir = self.settings.TEMP_DIR / "cloned_repos"
		self.clone_dir.mkdir(parents=True, exist_ok=True)
		self.ignore_patterns = [
			'.git', '__pycache__', 'node_modules', '.DS_Store',
			'*.pyc', '*.pyo', '*.o', '*.so', '*.egg',
			'dist', 'build', '.pytest_cache', '.ruff_cache'
		]

	def _get_repo_path(self, repo_url: str) -> Path:
		"""Generates a local path from a repo URL."""
		repo_name = repo_url.split('/')[-1].replace('.git', '')
		return self.clone_dir / repo_name

	def clone_repo(self, repo_url: str) -> Path:
		"""
		Clones a git repository. If it already exists, pulls the latest changes.
		Returns the local path to the repository.
		"""
		repo_path = self._get_repo_path(repo_url)

		if repo_path.exists():
			logger.info(f"Repo {repo_path.name} already exists. Fetching latest changes.")
			try:
				subprocess.run(
					['git', 'fetch'],
					cwd=repo_path,
					check=True,
					capture_output=True,
					text=True
				)
				# Reset to remote main/master
				remote_head = subprocess.run(
					['git', 'rev-parse', 'origin/main'],
					cwd=repo_path, capture_output=True, text=True
				).stdout.strip()
				if not remote_head:
					remote_head = subprocess.run(
						['git', 'rev-parse', 'origin/master'],
						cwd=repo_path, capture_output=True, text=True
					).stdout.strip()

				if remote_head:
					subprocess.run(
						['git', 'reset', '--hard', remote_head],
						cwd=repo_path, check=True, capture_output=True, text=True
					)
				logger.info("Repo updated successfully.")
			except subprocess.CalledProcessError as e:
				logger.error(f"Failed to update repo {repo_path.name}: {e.stderr}")
				raise
		else:
			logger.info(f"Cloning {repo_url} into {repo_path}...")
			try:
				subprocess.run(
					['git', 'clone', repo_url, str(repo_path)],
					check=True,
					capture_output=True,
					text=True
				)
				logger.info("Repo cloned successfully.")
			except subprocess.CalledProcessError as e:
				logger.error(f"Failed to clone repo {repo_url}: {e.stderr}")
				raise

		return repo_path

	def get_file_tree(self, repo_path: Path, max_items: int = 100) -> str:
		"""Generates a text-based file tree for the given path."""
		tree = []
		item_count = 0

		for root, dirs, files in os.walk(repo_path):
			# Exclude ignored directories
			dirs[:] = [d for d in dirs if d not in self.ignore_patterns]
			files[:] = [f for f in files if all(p not in f for p in self.ignore_patterns)]

			level = root.replace(str(repo_path), '').count(os.sep)
			indent = ' ' * 4 * level

			if item_count < max_items:
				tree.append(f"{indent}{os.path.basename(root)}/")
				item_count += 1

			sub_indent = ' ' * 4 * (level + 1)
			for f in sorted(files):
				if item_count >= max_items:
					tree.append(f"{sub_indent}...")
					return "\n".join(tree)
				tree.append(f"{sub_indent}{f}")
				item_count += 1

		return "\n".join(tree)

	def read_file_content(self, file_path: Path, max_lines: int = 500) -> str:
		"""Reads the content of a file, with a line limit."""
		if not file_path.is_file():
			return f"Error: File not found at {file_path}"
		try:
			with open(file_path, encoding='utf-8') as f:
				lines = f.readlines()

			if len(lines) > max_lines:
				content = "".join(lines[:max_lines]) + f"\n... (file truncated at {max_lines} lines)"
			else:
				content = "".join(lines)
			return content
		except Exception as e:
			return f"Error reading file: {e}"

	def search_in_codebase(self, repo_path: Path, query: str) -> str:
		"""
		Uses ripgrep (rg) to search the codebase.
		Falls back to git grep if rg is not available.
		"""
		try:
			# Use ripgrep with ignore files
			result = subprocess.run(
				['rg', '--max-count=10', '--no-heading', '-i', query, '.'],
				cwd=repo_path,
				check=True,
				capture_output=True,
				text=True,
				timeout=10
			)
			return result.stdout or "No results found."
		except (subprocess.CalledProcessError, FileNotFoundError):
			logger.warning("ripgrep (rg) not found or failed, falling back to git grep.")
			try:
				# Fallback to git grep
				result = subprocess.run(
					['git', 'grep', '-i', '-n', query],
					cwd=repo_path,
					check=True,
					capture_output=True,
					text=True,
					timeout=10
				)
				return result.stdout or "No results found."
			except (subprocess.CalledProcessError, FileNotFoundError):
				return "Error: Could not perform search. Neither ripgrep (rg) nor git are available."
		except subprocess.TimeoutExpired:
			return "Error: Search operation timed out."
