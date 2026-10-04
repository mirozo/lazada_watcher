import os
import httpx

API_BASE = "https://api.telegram.org"

class Telegram:
    def __init__(self, token: str, chat_id: str) -> None:
        self._url = f"{API_BASE}/bot{token}"
        self._chat_id = chat_id

    @classmethod
    def from_env(cls) -> "Telegram":
        return cls(os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"])
    
    def send(self, text: str) -> None:
        response = httpx.post(
            f"{self._url}/sendMessage",
            json={
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        response.raise_for_status()

def recent_chat_ids(token: str) -> dict[str, str]:
    response = httpx.get(f"{API_BASE}/bot{token}/getUpdates", timeout=15)
    response.raise_for_status()
    chats = {}

    for update in response.json()["result"]:
        event = update.get("message") or update.get("channel_post") or update.get("my_chat_member") or {}
        chat = event.get("chat")
        if chat:
            chats[str(chat["id"])] = chat.get("title") or chat.get("username") or chat.get("first_name", "")

    return chats
