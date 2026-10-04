import enum
import logging
from dataclasses import dataclass
from pathlib import Path
import random
import shutil
import time

from patchright.sync_api import Error as PlaywrightError
from patchright.sync_api import Route, sync_playwright

from lazada_watcher.config import Proxy

logger = logging.getLogger(__name__)

BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}
NAVIGATION_TIMEOUT_MS = 30_000
STOCK_RENDER_TIMEOUT_MS = 20_000

BLOCKED_URLS = [
    # ads
    "*://pagead2.googlesyndication.com/*",
    "*://googleads.g.doubleclick.net/*",
    # images
    "*.jpg*", "*.jpeg*", "*.png*", "*.webp*", "*.gif*", "*.avif*", "*.svg*", "*.ico*",
    # fonts
    "*.woff*", "*.woff2*", "*.ttf*", "*.otf*",
    # media
    "*.mp4*", "*.webm*", "*.m3u8*", "*.mp3*",
]

# Need to wait for JS to fetch stock information
DETECT_STOCK_JS = """
() => {
    const captcha = location.href.includes('punish')
        || document.querySelector('#baxia-dialog-content, iframe[src*="punish"], .nc_wrapper, #nocaptcha');
    if (captcha) return 'captcha';

    const buyButtons = [...document.querySelectorAll('.add-to-cart-buy-now-btn')]
        .map(button => button.innerText.trim().toLowerCase());

    if (buyButtons.some(text => text === "buy now" || text === "add to cart")) return 'in_stock';

    const warnings = [...document.querySelectorAll('.quantity-content-warning')]
        .map(warning => warning.innerText.toLowerCase());
    if (warnings.some(text => text.includes("out of stock"))) return 'out_of_stock';

    return null;
}
"""

READ_PRICE_JS = "() => document.querySelector('.pdp-v2-product-price-content-salePrice')?.innerText.trim() || null"

class Stock(enum.StrEnum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    CAPTCHA = "captcha"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StockResult:
    status: Stock
    price: str | None = None

def _block_heavy_resources(route: Route) -> None:
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        route.abort()
    else:
        route.continue_()

class StockChecker:
    def __init__(self, profile_dir: Path, headless: bool, channel: str, proxy: Proxy | None) -> None:
        self._profile_dir = profile_dir
        self._headless = headless
        self._channel = channel
        self._proxies = proxy.endpoints() if proxy else []
        self._session_seconds = proxy.session_seconds if proxy else 0
        self._proxy_index = random.randrange(len(self._proxies)) if self._proxies else 0
        self._session_started = 0.0

    def _launch_context(self) -> None:
        proxy = self._proxies[self._proxy_index] if self._proxies else None
        if proxy:
            logger.info("Using proxy %s", proxy["server"])
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self._profile_dir),
            channel=self._channel,
            headless=self._headless,
            no_viewport=True,
            proxy=proxy,
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        cdp = self._context.new_cdp_session(self._page)
        cdp.send("Network.enable")
        cdp.send("Network.setBlockedURLs", {"urls": BLOCKED_URLS})
        
        self._session_started = time.monotonic()

    def rotate_proxy(self) -> None:
        if len(self._proxies) < 2:
            return
        self._context.close()
        shutil.rmtree(self._profile_dir, ignore_errors=True)
        self._proxy_index = (self._proxy_index + 1) % len(self._proxies)
        self._launch_context()

    def _rotate_proxy_if_due(self) -> None:
        if time.monotonic() - self._session_started < self._session_seconds:
            return
        self.rotate_proxy()

    def __enter__(self) -> "StockChecker":
        self._playwright = sync_playwright().start()
        self._launch_context()
        return self
    
    def __exit__(self, *exc_info) -> None:
        self._context.close()
        self._playwright.stop()


    def check(self, url: str) -> StockResult:
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
            status = Stock(self._page.wait_for_function(DETECT_STOCK_JS, timeout=STOCK_RENDER_TIMEOUT_MS).json_value())
        except PlaywrightError as error:
            logger.warning("Could not determine stock for %s: %s", url, error.message.splitlines()[0])
            return StockResult(Stock.UNKNOWN)
        
        price = self._page.evaluate(READ_PRICE_JS) if status is Stock.IN_STOCK else None
        return StockResult(status, price)



