import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PARARIUS_URL = "https://www.pararius.com/apartments/tilburg"
SEEN_FILE = "seen_properties.json"

EMAIL = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL")


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)


def send_email(properties):
    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = "🏠 Nuevas propiedades encontradas"

    body = ""
    for p in properties:
        body += (
            f"{p['title']}\n"
            f"Precio: {p['price']}\n"
            f"Fuente: Pararius\n"
            f"Ver propiedad: {p['url']}\n\n"
        )

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)


def scrape():
    res = requests.get(PARARIUS_URL, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")

    listings = soup.select("section.listing-search-item")
    seen = load_seen()

    new_props = []
    seen_this_run = set()

    for item in listings:
        link = item.select_one("a.listing-search-item__link")
        price = item.select_one(".listing-search-item__price")

        if not link:
            continue

        url = "https://www.pararius.com" + link["href"]
        title = link.get_text(strip=True)
        price_text = price.get_text(strip=True) if price else "N/A"

        # 🔴 deduplicación en la misma ejecución
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


if __name__ == "__main__":
    changed = scrape()
    if changed:
        print("Nuevas propiedades encontradas")
    else:
        print("Sin cambios")
