import json
import os
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

    # Debug: prindi HTML struktuur kuulutuste piirkonnast
    body = soup.find("body")
    if body:
        print("  HTML struktuur (3000 tähemärki):")
        print(body.decode_contents()[:3000])

    return []


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("Tokenid puuduvad!")
        return

    config = laadi_config()
    url = config["search_url"]
    print(f"Kontrollin: {url}")
    kraabi_kuulutused(url)


if __name__ == "__main__":
    main()
