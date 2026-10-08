import json
import logging
import random
import time
from collections import Counter
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import Protocol
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from lazada_watcher.config import Config, Listing
from lazada_watcher.stock import Stock, StockResult

logger = logging.getLogger(__name__)

UNKNOWN_ALERT_THRESHOLD = 3
GAP_BETWEEN_LISTINGS_SECONDS = (3, 8)

class Checker(Protocol):
    def check(self, url: str) -> StockResult: ...
    def rotate_proxy(self) -> None: ...


def alert_message(listing: Listing, previous: Stock | None, result: StockResult) -> str | None:
    name = escape(listing.name)
    if result.status is Stock.IN_STOCK and previous is not Stock.IN_STOCK:
        price = f"\nPrice: {escape(result.price)}" if result.price else ""
        return f"🟢 IN STOCK: {name}{price}\n{listing.url}"
    
    if result.status is Stock.OUT_OF_STOCK and previous is Stock.IN_STOCK:
        return f"🔴 Sold out again: {name}"
    
    return None

class Watcher:
    def __init__(self, config: Config, checker: Checker, notify: Callable[[str], None]) -> None:
        self._config = config
        self._checker = checker
        self._notify = notify
        self._state = self._load_state()

        self._unknown_streaks: Counter[str] = Counter()
        self._captcha_alerted = False

    def _seconds_until_active(self) -> float:
        """0 if inside the active window, otherwise seconds until it next opens."""
        now = datetime.now(ZoneInfo(self._config.timezone))
        start = now.replace(hour=self._config.active_start_hour, minute=0, second=0, microsecond=0)
        end = now.replace(hour=self._config.active_end_hour, minute=0, second=0, microsecond=0)

        if start <= now < end:
            return 0
        if now < start:
            return (start - now).total_seconds()
        return (start + timedelta(days=1) - now).total_seconds()

    def run_forever(self) -> None:
        while True:
            wait = self._seconds_until_active()
            if wait:
                logger.info("Outside active hours, sleeping %.1f hours", wait / 3600)
                time.sleep(wait)
                continue

            if self.run_cycle():
                time.sleep(self._config.captcha_backoff_seconds)

            else:
                jitter = random.uniform(-self._config.poll_jitter_seconds, self._config.poll_jitter_seconds)
                time.sleep(max(1.0, self._config.poll_interval_seconds + jitter))

    def run_cycle(self) -> bool:
        """
        Check every listing once in random order.
        """
        listings = random.sample(self._config.listings, len(self._config.listings))
        for index, listing in enumerate(listings):
            result = self._checker.check(listing.url)
            logger.info("%s: %s%s", listing.name, result.status, f" ({result.price})" if result.price else "")

            if result.status is Stock.CAPTCHA:
                self._on_captcha(listing)
                return True
            
            if self._captcha_alerted and result.status is not Stock.UNKNOWN:
                # self._notify("✅ Captcha cleared, stock checks are working again.")
                self._captcha_alerted = False

            self._on_result(listing, result)

            if index < len(listings) - 1:
                time.sleep(random.uniform(*GAP_BETWEEN_LISTINGS_SECONDS))

        self._save_state()
        return False
    

    def _on_captcha(self, listing: Listing) -> None:
        self._checker.rotate_proxy()
        backoff_minutes = self._config.captcha_backoff_seconds / 60
        logger.warning("Captcha encountered, backing off for %.0f minutes", backoff_minutes)
        if not self._captcha_alerted:
            # self._notify(
            #     f"⚠️ Lazada served a captcha on {escape(listing.name)}. "
            #     f"Retrying every {backoff_minutes:.0f} minutes, you will get a message once it clears."
            # )
            self._captcha_alerted = True

    def _on_result(self, listing: Listing, result: StockResult) -> None:
        if result.status is Stock.UNKNOWN:
            self._unknown_streaks[listing.url] += 1
            if self._unknown_streaks[listing.url] == UNKNOWN_ALERT_THRESHOLD:
                self._notify(
                    f"⚠️ Could not read stock for {escape(listing.name)} {UNKNOWN_ALERT_THRESHOLD} times in a row. "
                    f"The listing may be gone or Lazada changed its page layout."
                )
            return
        
        self._unknown_streaks.pop(listing.url, None)
        if message := alert_message(listing, self._state.get(listing.url), result):
            self._notify(message)

        self._state[listing.url] = result.status


    def _load_state(self) -> dict[str, Stock]:
        path: Path = self._config.state_file
        if not path.exists():
            return {}
        
        return {url: Stock(status) for url, status in json.loads(path.read_text()).items()}
    
    def _save_state(self) -> None:
        self._config.state_file.write_text(json.dumps(self._state, indent=2))




