from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=".tmp-profile",
        channel="chrome",
        headless=False,
        proxy={"server": "http://sg.decodo.com:10001",
               "username": "spdohxx2ol", "password": "bltBhw=h04EctU00Zr"},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://ip.decodo.com/json")
    print(page.inner_text("body"))
    ctx.close()