import json
import os
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

CONFIG_FILE = "config.json"
NAHTUD_FILE = "nahtud_kuulutused.json"


def laadi_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def laadi_nahtud():
    if os.path.exists(NAHTUD_FILE):
        with open(NAHTUD_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def salvesta_nahtud(nahtud):
    with open(NAHTUD_FILE, "w", encoding="utf-8") as f:
        json.dump(list(nahtud), f)


def kraabi_kuulutused(url):
    kuulutused = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        leht = browser.new_page()
        leht.set_extra_http_headers({
            "Accept-Language": "et-EE,et;q=0.9,en;q=0.8"
        })

        leht.goto(url, wait_until="networkidle", timeout=30000)

        # Oota kuni kuulutused laetakse
        try:
            leht.wait_for_selector("article", timeout=10000)
        except Exception:
            print("  Kuulutuste laadimine aegus")

        html = leht.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    kaardid = soup.select("article")
    print(f"  Leitud article elemente: {len(kaardid)}")

    for kaart in kaardid:
        kuulutuse_id = (
            kaart.get("data-id") or
            kaart.get("id") or
            kaart.get("data-object-id", "")
        )
        if not kuulutuse_id:
            continue

        pealkiri_el = kaart.select_one(".object-title, h2, h3, .title")
        pealkiri = pealkiri_el.get_text(strip=True) if pealkiri_el else "—"

        hind_el = kaart.select_one(".object-price-value, .price, [class*='price']")
        hind = hind_el.get_text(strip=True) if hind_el else "—"

        aadress_el = kaart.select_one(".object-address, .address, [class*='address']")
        aadress = aadress_el.get_text(strip=True) if aadress_el else "—"

        link_el = kaart.select_one("a[href]")
        link = link_el["href"] if link_el else ""
        if link and not link.startswith("http"):
            link = "https://www.kv.ee" + link

        kuulutused.append({
            "id": str(kuulutuse_id),
            "pealkiri": pealkiri,
            "hind": hind,
            "aadress": aadress,
            "link": link,
        })

    return kuulutused


def saada_telegram_teade(token, chat_id, kuulutus):
    import requests
    tekst = (
        f"🏠 *Uus kuulutus kv.ee*\n\n"
        f"📍 {kuulutus['aadress']}\n"
        f"💶 {kuulutus['hind']}\n"
        f"📝 {kuulutus['pealkiri']}\n\n"
        f"🔗 [Vaata kuulutust]({kuulutus['link']})"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": tekst,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }, timeout=10)
        if not resp.ok:
            print(f"Telegram viga: {resp.text}")
    except requests.RequestException as e:
        print(f"Telegram ühenduse viga: {e}")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN ja TELEGRAM_CHAT_ID peavad olema seadistatud!")
        return

    config = laadi_config()
    nahtud = laadi_nahtud()

    url = config["search_url"]
    print(f"Kontrollin: {url}")

    kuulutused = kraabi_kuulutused(url)
    print(f"Leitud {len(kuulutused)} kuulutust")

    uued = 0
    for k in kuulutused:
        if k["id"] not in nahtud:
            nahtud.add(k["id"])
            saada_telegram_teade(token, chat_id, k)
            print(f"UUUS: {k['aadress']} — {k['hind']}")
            uued += 1
            time.sleep(1)

    salvesta_nahtud(nahtud)
    print(f"Uusi kuulutusi: {uued}")


if __name__ == "__main__":
    main()
