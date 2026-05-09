import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

AGENCY_NAME = os.getenv("AGENCY_NAME", "Sexy Prime")

DB_PATH = os.getenv("DB_PATH", "bot_votacao.db")
