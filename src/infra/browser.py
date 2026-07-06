from playwright.async_api import async_playwright, Browser

from core.base.base_lifespan import BaseLifecycle


class BrowserStopped:
    pass


class BrowserRunning:
    def __init__(self, browser: Browser):
        self._browser = browser

    def get(self) -> Browser:
        return self._browser


class BrowserProvider(BaseLifecycle):
    def __init__(self, browser_type: str = "chromium"):
        self.browser_type = browser_type
        self._pw = None
        self._state: BrowserStopped | BrowserRunning = BrowserStopped()

    async def start(self) -> None:
        self._pw = await async_playwright().start()

        launcher = {
            "chromium": self._pw.chromium,
            "firefox": self._pw.firefox,
            "webkit": self._pw.webkit,
        }.get(self.browser_type)

        if not launcher:
            raise ValueError(f"Unknown browser type: {self.browser_type}")

        browser = await launcher.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
            ],
        )

        self._state = BrowserRunning(browser)

    def get_instance(self) -> Browser:
        if isinstance(self._state, BrowserStopped):
            raise RuntimeError("Browser not started. Call lifespan.start() first.")

        return self._state.get()

    async def stop(self) -> None:
        if isinstance(self._state, BrowserRunning):
            await self._state.get().close()

        if self._pw:
            await self._pw.stop()

        self._state = BrowserStopped()
        self._pw = None
