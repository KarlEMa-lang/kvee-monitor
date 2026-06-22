"""
Käivita see skript üks kord, et saada oma Telegram chat_id.
Pärast käivitamist saada oma botile Telegramis sõnum "/start"
ja skript kuvab sinu chat_id, mille pead config.json-i sisestama.
"""
import json
import requests
import time

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

token = config["telegram"]["bot_token"]

if token == "SIIA_BOTI_TOKEN":
    print("Sisesta esmalt bot_token config.json faili!")
    exit(1)

print("Saada oma botile Telegramis suvaline sõnum...")
print("Ootan...")

url = f"https://api.telegram.org/bot{token}/getUpdates"

for _ in range(30):
    resp = requests.get(url, timeout=10).json()
    updates = resp.get("result", [])
    if updates:
        for update in updates:
            msg = update.get("message", {})
            chat = msg.get("chat", {})
            chat_id = chat.get("id")
            nimi = chat.get("first_name", "")
            if chat_id:
                print(f"\nLeitud! Sinu chat_id on: {chat_id}")
                print(f"Kasutaja: {nimi}")
                print(f'\nLisab automaatselt config.json faili...')
                config["telegram"]["chat_id"] = str(chat_id)
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print("config.json uuendatud!")
                exit(0)
    time.sleep(2)

print("Ei saanud vastust. Proovi uuesti ja saada botile sõnum.")
