#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------- CONFIG ---------------- #
SEEN_FILE = "/app/data/seen_properties.json"

EMAIL = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL")

PARARIUS_URL = "https://www.pararius.com/apartments/utrecht"  # Cambiá la ciudad si querés

# ---------------- FUNCIONES ---------------- #
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, indent=2)

def send_email(properties):
    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = f"🏠 {len(properties)} nuevas propiedades encontradas"

    html = "<h2>🏠 Nuevas propiedades encontradas</h2><hr>"
    for p in properties:
        html += f"""
        <p>
        <strong>{p['title']}</strong><br>
        Precio: {p['price']}<br>
        <a href="{p['url']}">Ver propiedad</a>
        </p><hr>
        """

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        print(f"✅ Email enviado con {len(properties)} propiedad(es)")
    except Exception as e:
        print(f"❌ Error enviando email: {e}")

def scrape():
    try:
        res = requests.get(PARARIUS_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if res.status_code != 200:
            print(f"⚠️ Error HTTP {res.status_code}")
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        listings = soup.select("section.listing-search-item")

        seen = load_seen()
        new_props = []
        seen_this_run = set()

        for item in listings:
            link_tag = item.select_one("a.listing-search-item__link")
            price_tag = item.select_one(".listing-search-item__price")
            title_tag = item.select_one(".listing-search-item__title")

            if not link_tag or not price_tag:
                continue

            url = "https://www.pararius.com" + link_tag["href"]
            if url in seen or url in seen_this_run:
                continue

            title = title_tag.get_text(strip=True) if title_tag else "Departamento"
            price = price_tag.get_text(strip=True)

            new_props.append({
                "title": title,
                "price": price,
                "url": url
            })
            seen_this_run.add(url)

        if new_props:
            send_email(new_props)
            seen.update(seen_this_run)
            save_seen(seen)
        return new_props

    except Exception as e:
        print(f"❌ Error scraping Pararius: {e}")
        return []

# ---------------- LOOP 24/7 ---------------- #
if __name__ == "__main__":
    print("🏠 Bot de Alquileres iniciado...")
    while True:
        new_properties = scrape()
        if new_properties:
            print(f"✅ {len(new_properties)} nueva(s) propiedad(es) encontradas")
        else:
            print("ℹ️ Sin propiedades nuevas")
        print("⏱ Esperando 5 minutos...")
        time.sleep(300)  # 5 minutos
