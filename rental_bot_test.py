#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import json
import re

# ---------------- ARCHIVO DE ESTADO ---------------- #
SENT_FILE = "seen_properties.json"

# ---------------- CONFIG desde ENV ---------------- #
EMAIL_CONFIG = {
    "sender_email": os.getenv("SENDER_EMAIL"),
    "receiver_email": os.getenv("RECEIVER_EMAIL"),
    "password": os.getenv("EMAIL_PASSWORD"),
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465
}

SEARCH_CONFIG = {
    "city": os.getenv("CITY", "utrecht"),
    "min_price": int(os.getenv("MIN_PRICE", 1000)),
    "max_price": int(os.getenv("MAX_PRICE", 1500))
}

# ---------------- BOT ---------------- #
class RentalBotParariusEnv:

    def __init__(self):
        self.sent_links = self.load_sent_links()
        self.new_properties = []

    def load_sent_links(self):
        if os.path.exists(SENT_FILE):
            try:
                with open(SENT_FILE, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def save_sent_links(self):
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(self.sent_links)), f, indent=2)

    def fetch_properties_pararius(self):
        url = f"https://www.pararius.com/apartments/{SEARCH_CONFIG['city']}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9"
        }

        print(f"🔍 Buscando Pararius: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                print(f"❌ Pararius HTTP {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            listings = soup.select(
                "section.listing-search-item, li.search-list__item--listing"
            )

            properties = []

            for item in listings:
                link_tag = item.select_one("a[href]")
                price_tag = item.select_one(
                    ".listing-search-item__price, .listing-price"
                )
                title_tag = item.select_one(
                    ".listing-search-item__title, h2"
                )

                if not link_tag or not price_tag:
                    continue

                url_prop = link_tag["href"]
                if not url_prop.startswith("http"):
                    url_prop = "https://www.pararius.com" + url_prop

                if url_prop in self.sent_links:
                    continue

                price_match = re.search(r"€\s?([\d.,]+)", price_tag.text)
                if not price_match:
                    continue

                price_val = int(
                    price_match.group(1)
                    .replace(".", "")
                    .replace(",", "")
                )

                if not (
                    SEARCH_CONFIG["min_price"]
                    <= price_val
                    <= SEARCH_CONFIG["max_price"]
                ):
                    continue

                title = (
                    title_tag.text.strip()
                    if title_tag else "Departamento"
                )

                properties.append({
                    "title": title,
                    "price": f"€ {price_val}",
                    "location": SEARCH_CONFIG["city"].title(),
                    "url": url_prop,
                    "source": "Pararius",
                    "found_at": datetime.now().isoformat()
                })

            print(f"✅ Pararius: {len(properties)} nuevas propiedades")
            return properties

        except Exception as e:
            print(f"❌ Error Pararius: {e}")
            return []

    def send_email(self):
        if not self.new_properties:
            print("ℹ️ No hay nuevas propiedades para enviar")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"🏠 {len(self.new_properties)} nuevas propiedades en "
            f"{SEARCH_CONFIG['city'].title()}"
        )
        msg["From"] = EMAIL_CONFIG["sender_email"]
        msg["To"] = EMAIL_CONFIG["receiver_email"]

        html = "<h2>🏠 Nuevas propiedades encontradas</h2><hr>"

        for p in self.new_properties:
            html += f"""
            <p>
                <strong>{p['title']}</strong><br>
                Precio: {p['price']}<br>
                Fuente: {p['source']}<br>
                <a href="{p['url']}">Ver propiedad</a>
            </p>
            <hr>
            """

        msg.attach(MIMEText(html, "html"))

        print("📤 Enviando email...")

        try:
            with smtplib.SMTP_SSL(
                EMAIL_CONFIG["smtp_server"],
                EMAIL_CONFIG["smtp_port"]
            ) as server:
                server.login(
                    EMAIL_CONFIG["sender_email"],
                    EMAIL_CONFIG["password"]
                )
                server.send_message(msg)

        except Exception as e:
            print(f"❌ Error enviando email: {e}")
            return

        for p in self.new_properties:
            self.sent_links.add(p["url"])

        self.save_sent_links()
        print("✅ Email enviado correctamente")

    def run(self):
        print("=" * 60)
        print("🏠 BOT DE ALQUILERES (Pararius - ENV)")
        print(
            f"📍 Ciudad: {SEARCH_CONFIG['city'].title()} | "
            f"Rango: €{SEARCH_CONFIG['min_price']} - "
            f"€{SEARCH_CONFIG['max_price']}"
        )
        print("=" * 60)

        self.new_properties = self.fetch_properties_pararius()

        if not self.new_properties:
            print("ℹ️ No hay propiedades nuevas. Fin.")
            return

        self.send_email()

        print("🏁 Ejecución finalizada")
        print("=" * 60)


if __name__ == "__main__":
    bot = RentalBotParariusEnv()
    bot.run()
