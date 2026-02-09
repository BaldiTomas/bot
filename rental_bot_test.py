#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
from datetime import datetime

# Archivo para guardar links ya enviados
SEEN_FILE = "seen_properties.json"

# Configuración desde variables de entorno
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL")

# URL Pararius
PARARIUS_URL = "https://www.pararius.com/apartments/utrecht/1000-1500"

# ----------------------------------------
# Funciones para manejar propiedades ya vistas
# ----------------------------------------
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, indent=2)

# ----------------------------------------
# Función para enviar email
# ----------------------------------------
def send_email(properties):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = TO_EMAIL
    msg["Subject"] = f"🏠 {len(properties)} nuevas propiedades en Utrecht"

    html = "<h2>🏠 Nuevas propiedades encontradas</h2><hr>"
    for p in properties:
        html += f"""
        <p>
        <strong>{p['title']}</strong><br>
        Precio: {p['price']}<br>
        <a href="{p['url']}">Ver propiedad</a><br>
        Fuente: Pararius
        </p><hr>
        """

    msg.attach(MIMEText(html, "html"))

    print(f"📤 Enviando email con {len(properties)} propiedades...")
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print("✅ Email enviado correctamente")
    except Exception as e:
        print(f"❌ Error enviando email: {e}")

# ----------------------------------------
# Función principal de scraping
# ----------------------------------------
def scrape():
    print("🔍 Conectando a Pararius...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        res = requests.get(PARARIUS_URL, headers=headers, timeout=20)
        if res.status_code != 200:
            print(f"❌ Error HTTP {res.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error conectando a Pararius: {e}")
        return False

    soup = BeautifulSoup(res.text, "html.parser")
    listings = soup.select("section.listing-search-item")
    print(f"📋 Encontrados {len(listings)} listings en la página")

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
        title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
        price_text = price_tag.get_text(strip=True)

        # Deduplicación
        if url in seen or url in seen_this_run:
            continue

        seen_this_run.add(url)
        new_props.append({
            "title": title,
            "price": price_text,
            "url": url
        })

    if new_props:
        send_email(new_props)
        seen.update(seen_this_run)
        save_seen(seen)
        return True

    return False

# ----------------------------------------
# Ejecutar bot
# ----------------------------------------
if __name__ == "__main__":
    print("="*50)
    print("🏠 BOT DE ALQUILERES - Pararius")
    print(f"📍 URL: {PARARIUS_URL}")
    print("="*50)

    changed = scrape()

    if changed:
        print("✅ Nuevas propiedades encontradas y enviadas")
    else:
        print("ℹ️ Sin propiedades nuevas")
    
    print("🏁 Ejecución finalizada")
    print("="*50)
