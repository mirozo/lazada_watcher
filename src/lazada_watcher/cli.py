import argparse
import logging
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

from lazada_watcher.config import Config, load_config
from lazada_watcher.stock import StockChecker
from lazada_watcher.telegram import Telegram, recent_chat_ids
from lazada_watcher.watcher import GAP_BETWEEN_LISTINGS_SECONDS, Watcher

logger = logging.getLogger("lazada_watcher")

def _checker(config: Config) -> StockChecker:
    return StockChecker(config.profile_dir, config.headless, config.browser_channel, config.proxy)

def watch(config: Config) -> None:
    telegram = Telegram.from_env()
    telegram.send(f"👀 Lazada watcher started, watching {len(config.listings)} listing(s).")

    try:
        with _checker(config) as checker:
            Watcher(config, checker, telegram.send).run_forever()
    except KeyboardInterrupt:
        telegram.send("Lazada watcher manually stopped.")
    except Exception as error:
        telegram.send(f"💥 Lazada watcher crashed: {type(error).__name__}: {error}")
        raise


def check(config: Config) -> None:
    with _checker(config) as checker:
        for index, listing in enumerate(config.listings):
            if index:
                time.sleep(random.uniform(*GAP_BETWEEN_LISTINGS_SECONDS))
            result = checker.check(listing.url)
            logger.info(f"{result.status:<13} {result.price or '':<10} {listing.name}")



def telegram_chat_id() -> None:
    chats = recent_chat_ids(os.environ["TELEGRAM_BOT_TOKEN"])
    if not chats:
        logger.info("No messages found. Send any message to your bot in Telegram, then run this again")

    for chat_id, name in chats.items():
        logger.info(f"{chat_id}\t{name}")



def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(prog="lazada-watcher")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("watch", help="Poll listings forever and alert on stock changes")
    commands.add_parser("check", help="Check every listing once and print the result")
    commands.add_parser("telegram-chat-id", help="List chats that have messaged your bot")
    commands.add_parser("telegram-test", help="Send a test message to TELEGRAM_CHAT_ID")
    args = parser.parse_args()

    match args.command:
        case "watch":
            watch(load_config(args.config))

        case "check":
            check(load_config(args.config))

        case "telegram-chat-id":
            telegram_chat_id()

        case "telegram-test":
            Telegram.from_env().send("✅ Lazada watcher can reach you.")
