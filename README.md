# Lazada Watcher

## Prerequisites

### Telegram bot

Please add the following telegram IDs to the `.env` file.

```
TELEGRAM_BOT_TOKEN=<TODO>
TELEGRAM_CHAT_ID=<TODO>
```

You can find out your `TELEGRAM_CHAT_ID` by the following after specifying your `TELEGRAM_BOT_TOKEN`:

```
uv run lazada-watcher telegram_chat_id
```

which will print out the bot's recent chats.

### Proxies

Lazada will throw Captchas very quickly if rotating residential proxies are not used.

Specify your residential proxies to use in the following format in `lazada_watcher/config.yaml`.

```
proxy:
  host: sg.decodo.com
  username: spdohxx2ol
  start_port: 10001
  count: 50            # raise this to expand the pool
  session_seconds: 600 # 10 min sticky session
```

If your proxy requires a password, add that to the `.env` file.

```
PROXY_PASSWORD=<TODO>
```

## Quick Start

### 1. Add your Lazada Product URLs to `lazada_watcher/config.yaml`

```
listings:
  - name: "Pokemon TCG 30th Booster Bundle"
    url: "https://www.lazada.sg/products/pdp-i13933878257-s124956048317.html"
  - name: "Pokemon TCG 30th Binder Collection"
    url: "https://www.lazada.sg/products/pdp-i13858060495-s124858893178.html"
  - name: "Pokemon TCG Ascended Heroes Booster Bundle"
    url: "https://www.lazada.sg/products/pdp-i13696744288-s124594658123.html"
  - name: "Pokemon TCG Ascended Heroes Deluxe Pin Set"
    url: "https://www.lazada.sg/products/pdp-i13664766505-s124315805988.html"
  - name: "Pokemon TCG 30th 2 Pack Blister"
    url: "https://www.lazada.sg/products/pdp-i13855587802-s124858735825.html"
```

### 2. Run the following commands

```
uv sync
uv run lazada-watcher check # to check if individual URLs are reachable

uv run lazada-watcher watch # runs forever, with the polling settings specified in `config.yaml`
```

### 3. Wait and profit! 

A telegram message will be sent to the specified chat once stocks are available. Snap up the goods ASAP!
