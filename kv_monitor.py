import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup

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
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "et-EE,et;q=0.9,en;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        print(f"  HTTP vastus: {resp.status_code}")
    except requests.RequestException as e:
        print(f"Viga: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    kuulutused = {}

    # Leia kõik pildilinkide kaudu kuulutuse ID-d
    for a in soup.find_all("a", href=True):
        m = re.search(r'/object/images/(\d+)', a["href"])
        if not m:
            continue
        kuulutuse_id = m.group(1)
        if kuulutuse_id in kuulutused:
            continue

        # Leia vanemelement (kuulutuse kaart)
        kaart = a.find_parent("article") or a.find_parent("li") or a.find_parent("div")

        pealkiri = "—"
        hind = "—"
        aadress = "—"

        if kaart:
            pealkiri_el = kaart.select_one(".object-title, h2, h3, .title, [class*='title']")
            if pealkiri_el:
                pealkiri = pealkiri_el.get_text(strip=True)

            hind_el = kaart.select_one("[class*='price']")
            if hind_el:
                hind = hind_el.get_text(strip=True)

            aadress_el = kaart.select_one("[class*='address'], [class*='location']")
            if aadress_el:
                aadress = aadress_el.get_text(strip=True)

        kuulutused[kuulutuse_id] = {
            "id": kuulutuse_id,
            "pealkiri": pealkiri,
            "hind": hind,
            "aadress": aadress,
            "link": f"https://www.kv.ee/{kuulutuse_id}",
        }

    return list(kuulutused.values())


def saada_telegram_teade(token, chat_id, kuulutus):
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
        print("Tokenid puuduvad!")
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
            print(f"UUUS: {k['link']}")
            uued += 1
            time.sleep(1)

    salvesta_nahtud(nahtud)
    print(f"Uusi kuulutusi: {uued}")


if __name__ == "__main__":
    main()
