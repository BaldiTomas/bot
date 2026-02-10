#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import re
import requests
from bs4 import BeautifulSoup

# ---------------- CONFIG ---------------- #
SEEN_FILE = "/app/data/seen_properties.json"  # Persistente en Railway/Docker

# Telegram Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PARARIUS_URL = os.getenv("CITY_URL", "https://www.pararius.com/apartments/utrecht")
MIN_PRICE = int(os.getenv("MIN_PRICE", 1000))
MAX_PRICE = int(os.getenv("MAX_PRICE", 1500))
SLEEP_MINUTES = int(os.getenv("SLEEP_MINUTES", 5))

# ---------------- FUNCIONES ---------------- #
def load_seen():
    """Carga las propiedades ya vistas"""
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    """Guarda las propiedades vistas"""
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, indent=2)

def parse_price(price_text):
    """Convierte un string de precio en int. Retorna None si no se puede parsear."""
    match = re.search(r"€\s*([\d,.]+)", price_text)
    if match:
        return int(match.group(1).replace(".", "").replace(",", ""))
    return None

def send_telegram(properties):
    """Envía notificación a Telegram con las nuevas propiedades"""
    if not properties:
        return
    
    # Construir mensaje
    message = f"🏠 <b>{len(properties)} Nueva(s) Propiedad(es) Encontrada(s)</b>\n\n"
    
    for i, prop in enumerate(properties, 1):
        message += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"<b>#{i}: {prop['title']}</b>\n"
        message += f"💰 {prop['price']}\n"
        message += f"🔗 <a href=\"{prop['url']}\">Ver Propiedad</a>\n\n"
    
    message += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"📊 Total rastreadas: {len(load_seen())}"
    
    # Enviar a Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Mensaje de Telegram enviado con {len(properties)} propiedad(es)")
        else:
            print(f"❌ Error Telegram: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")

def scrape():
    """Scraping de Pararius"""
    try:
        res = requests.get(
            PARARIUS_URL, 
            headers={"User-Agent": "Mozilla/5.0"}, 
            timeout=20
        )
        
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
            
            # Evitar duplicados en la misma ejecución y en el historial
            if url in seen or url in seen_this_run:
                continue

            title = title_tag.get_text(strip=True) if title_tag else "Departamento"
            price_text = price_tag.get_text(strip=True)
            price_val = parse_price(price_text)

            # Filtrar por rango de precio
            if price_val is None or not (MIN_PRICE <= price_val <= MAX_PRICE):
                continue

            new_props.append({
                "title": title,
                "price": price_text,
                "url": url
            })
            seen_this_run.add(url)

        # Si hay propiedades nuevas, enviar y guardar
        if new_props:
            send_telegram(new_props)
            seen.update(seen_this_run)
            save_seen(seen)

        return new_props

    except Exception as e:
        print(f"❌ Error scraping Pararius: {e}")
        return []

# ---------------- LOOP 24/7 ---------------- #
if __name__ == "__main__":
    print("=" * 50)
    print("🏠 Bot de Alquileres - Telegram Edition")
    print("=" * 50)
    print(f"📍 URL: {PARARIUS_URL}")
    print(f"💰 Rango: €{MIN_PRICE} - €{MAX_PRICE}")
    print(f"⏱️  Intervalo: {SLEEP_MINUTES} minutos")
    print(f"📱 Chat ID: {TELEGRAM_CHAT_ID}")
    print("=" * 50)
    print()
    
    # Verificar configuración
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ ERROR: Faltan variables de entorno")
        print("   TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID son requeridas")
        exit(1)
    
    print("✅ Bot iniciado correctamente\n")
    
    iteration = 0
    while True:
        iteration += 1
        print(f"🔄 Iteración #{iteration} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        new_properties = scrape()
        
        if new_properties:
            print(f"✅ {len(new_properties)} nueva(s) propiedad(es) encontradas")
        else:
            print("ℹ️ Sin propiedades nuevas")
        
        print(f"⏱️  Esperando {SLEEP_MINUTES} minutos...\n")
        time.sleep(SLEEP_MINUTES * 60)