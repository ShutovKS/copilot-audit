import logging

from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class WebInspector:
	"""
	A tool for autonomous web inspection.
	Extracts semantic structure (buttons, inputs, links) to help LLM guess locators.
	"""

	async def inspect_page(self, url: str) -> str:
		logger.info(f"WebInspector: Visiting {url}...")
		try:
			async with async_playwright() as p:
				browser = await p.chromium.launch(headless=True)
				context = await browser.new_context(
					viewport={'width': 1280, 'height': 800},
					user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
				)
				page = await context.new_page()

				try:
					await page.goto(url, wait_until="domcontentloaded", timeout=15000)
					await page.wait_for_timeout(2000)  # Allow hydration
				except PlaywrightTimeoutError:
					logger.warning(f"Timeout visiting {url}, extracting what loaded.")

				# Extract Accessibility Tree / Simplified DOM
				content = await page.content()
				structure = self._parse_html_to_context(content)

				await browser.close()
				return structure

		except Exception as e:
			logger.error(f"Inspection failed: {e}")
			return f"Error inspecting {url}: {str(e)}"

	def _parse_html_to_context(self, html: str) -> str:
		soup = BeautifulSoup(html, 'html.parser')

		elements = []

		# 1. Interactive Elements
		for tag in soup.find_all(['button', 'a', 'input', 'select', 'textarea', 'label']):
			elem_info = self._get_element_info(tag)
			if elem_info:
				elements.append(elem_info)

		# 2. Semantic Containers (headers, cards)
		for tag in soup.find_all(['h1', 'h2', 'h3', 'div']):
			# Heuristic: Keep divs with interesting classes/ids
			if tag.name == 'div':
				attrs = str(tag.attrs.get('class', '')) + str(tag.attrs.get('id', '')) + str(tag.attrs.get('data-testid', ''))
				if not any(k in attrs.lower() for k in ['card', 'panel', 'form', 'container', 'wrapper']):
					continue

			elem_info = self._get_element_info(tag, include_text=True)
			if elem_info and len(elem_info) < 200:  # Skip huge blobs
				elements.append(elem_info)

		# Deduplicate and Format
		unique_elements = sorted(list(set(elements)))
		return "\n".join(unique_elements[:150])  # Limit context window

	def _get_element_info(self, tag, include_text=True) -> str:
		name = tag.name
		text = tag.get_text(strip=True)[:50] if include_text else ""

		attrs = []
		if tag.get('id'):
			attrs.append(f"id='{tag.get('id')}'")
		if tag.get('data-testid'):
			attrs.append(f"data-testid='{tag.get('data-testid')}'")
		if tag.get('name'):
			attrs.append(f"name='{tag.get('name')}'")
		if tag.get('placeholder'):
			attrs.append(f"placeholder='{tag.get('placeholder')}'")
		if tag.get('role'):
			attrs.append(f"role='{tag.get('role')}'")
		if tag.get('type'):
			attrs.append(f"type='{tag.get('type')}'")

		# Class heuristic: only keep meaningful BEM-like classes
		classes = tag.get('class', [])
		meaningful_classes = [c for c in classes if any(x in c for x in ['btn', 'input', 'card', 'nav', 'menu', 'item'])]
		if meaningful_classes:
			classes_str = " ".join(meaningful_classes)
			attrs.append(f"class='{classes_str}'")

		attr_str = " ".join(attrs)

		if not attr_str and not text:
			return ""

		return f"<{name} {attr_str}>{text}</{name}>"

	async def check_locators_exist(self, url: str, locators: list[str]) -> list[str]:
		"""
		Performs a 'dry run' to see if locators exist on a live page.
		Returns a list of locators that were NOT found.
		"""
		if not locators:
			return []

		logger.info(f"WebInspector: Dry-running {len(locators)} locators on {url}...")
		missing_locators = []

		try:
			async with async_playwright() as p:
				browser = await p.chromium.launch(headless=True)
				context = await browser.new_context(viewport={'width': 1280, 'height': 800})
				page = await context.new_page()

				try:
					await page.goto(url, wait_until="domcontentloaded", timeout=15000)
				except PlaywrightTimeoutError:
					logger.error(f"Dry Run: Timeout visiting {url}. Cannot check locators.")
					await browser.close()
					# Return all locators as missing if page fails to load
					return locators

				for locator in locators:
					try:
						# Use a short timeout to quickly check for presence
						count = await page.locator(locator).count()
						if count == 0:
							missing_locators.append(locator)
					except PlaywrightTimeoutError:
						# If the locator is bad and causes a timeout
						missing_locators.append(locator)

				await browser.close()

		except Exception as e:
			logger.error(f"Dry Run failed unexpectedly: {e}")
			# In case of a total Playwright failure, we can't be sure, so return empty
			return []

		if missing_locators:
			logger.warning(f"Dry Run: Found {len(missing_locators)} missing locators.")
		else:
			logger.info("Dry Run: All locators found.")

		return missing_locators
