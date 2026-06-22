import json
import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlencode

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


def ehita_otsingu_url(filters):
    params = {}

    if filters.get("asukoht"):
        params["county"] = filters["asukoht"]
    piirkond = filters.get("piirkond")
    if isinstance(piirkond, list):
        params["parish[]"] = piirkond
    elif piirkond:
        params["parish[]"] = [piirkond]

    base_url = "https://www.kv.ee/search"
    return f"{base_url}?{urlencode(params, doseq=True)}"


def kraabi_kuulutused(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "et-EE,et;q=0.9,en;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Viga laadimisel: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    kuulutused = []

    for kaart in soup.select("article[data-id]"):
        kuulutuse_id = kaart.get("data-id", "")
        if not kuulutuse_id:
            continue

        pealkiri_el = kaart.select_one(".object-title, h2, .title")
        pealkiri = pealkiri_el.get_text(strip=True) if pealkiri_el else "—"

        hind_el = kaart.select_one(".object-price-value, .price")
        hind = hind_el.get_text(strip=True) if hind_el else "—"

        aadress_el = kaart.select_one(".object-address, .address")
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
    # Tokeni ja chat_id loeb GitHub Secretsist (keskkonnamuutujad)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN ja TELEGRAM_CHAT_ID peavad olema seadistatud!")
        return

    config = laadi_config()
    nahtud = laadi_nahtud()

    otsi_url = ehita_otsingu_url(config["filters"])
    print(f"Kontrollin: {otsi_url}")

    kuulutused = kraabi_kuulutused(otsi_url)
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
