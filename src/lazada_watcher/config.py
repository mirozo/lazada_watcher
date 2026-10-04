from dataclasses import dataclass
import os
from pathlib import Path
import random

import yaml

@dataclass(frozen=True)
class Listing:
    name: str
    url: str

@dataclass(frozen=True)
class Proxy:
    host: str
    username: str
    start_port: int
    count: int = 1
    session_seconds: float = 600
    port_per_endpoint: bool = True

    def endpoints(self) -> list[dict]:
        password = os.environ["PROXY_PASSWORD"]
        return [
            {
                "server": f"http://{self.host}:{self.start_port + (i if self.port_per_endpoint else 0)}",
                "username": self.username.format(session=random.randint(10_000_000, 99_999_999)),
                "password": password,
            }
            for i in range(self.count)
        ]


@dataclass(frozen=True)
class Config:
    listings: list[Listing]
    poll_interval_seconds: float = 60
    poll_jitter_seconds: float = 15
    captcha_backoff_seconds: float = 30
    headless: bool = False
    browser_channel: str = "chrome"
    proxy: Proxy | None = None
    profile_dir: Path = Path(".browser-profile")
    state_file: Path = Path("state.json")
    active_start_hour: int = 10
    active_end_hour: int = 19
    timezone: str = "Asia/Singapore"


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(path.read_text())
    listings = [
        Listing(name=item["name"], url=item["url"]) for item in raw.pop("listings")
    ]
    if not listings:
        raise ValueError(f"Np listings configured in {path}")
    
    for key in ("profile_dir", "state_file"):
        if key in raw:
            raw[key] = Path(raw[key])

    if "proxy" in raw:
        raw["proxy"] = Proxy(**raw["proxy"])

    return Config(listings=listings, **raw)

