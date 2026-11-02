"""
Version GitHub Actions : chaque lancement fait 3 vérifications (t=0, 2, 4 min)
des 2 pages de vente Opening Session Verbier, puis s'arrête.
Le workflow se relance toutes les 5 min => ~1 vérification / 2 min.
Le nom du topic ntfy vient du secret GitHub NTFY_TOPIC.
"""

import os
import sys
import time
import requests

TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
TEST = os.environ.get("TEST", "").lower() == "true"

PAGES = {
    "Billet seul": "https://verbier4vallees.ch/en/online-shop/activities/opening-session_activity_410650",
    "Billet + train": "https://verbier4vallees.ch/en/online-shop/activities/opening-session-st.nicholas-express_activity_426820",
}

PASSES = 3            # nombre de vérifications par lancement
PAUSE_SECONDES = 120  # 2 minutes entre chaque
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; verbier-watch)"}


def notifier(titre, message, lien=None):
    headers = {"Title": titre.encode("utf-8"), "Priority": "urgent"}
    if lien:
        headers["Click"] = lien
    requests.post(f"https://ntfy.sh/{TOPIC}", data=message.encode("utf-8"),
                  headers=headers, timeout=20)


def est_ouvert(url):
    """True = en vente, False = fermé/épuisé, None = page mal chargée."""
    html = requests.get(url, timeout=20, headers=HEADERS).text
    if "Opening Session" not in html:
        return None
    bas = html.lower()
    ferme = any(m in bas for m in (
        "not bookable", "sold out", "ausverkauft", "pas réservable", "complet"))
    return not ferme


def main():
    if not TOPIC:
        sys.exit("Secret NTFY_TOPIC manquant : ajoute-le dans Settings > Secrets > Actions.")

    if TEST:
        notifier("Verbier : test", "Test OK, les notifications fonctionnent.",
                 list(PAGES.values())[0])
        print("Notification de test envoyée.")

    for i in range(PASSES):
        for nom, url in PAGES.items():
            try:
                ouvert = est_ouvert(url)
            except Exception as e:
                print(f"{nom} : erreur {e}")
                continue
            etat = "OUVERT !" if ouvert else "fermé" if ouvert is False else "page illisible"
            print(f"[{time.strftime('%H:%M:%S')}] {nom} : {etat}")
            if ouvert is True:
                notifier(f"Verbier 5 CHF : {nom}",
                         f"{nom} : des billets sont en vente ! Fonce.", url)
        if i < PASSES - 1:
            time.sleep(PAUSE_SECONDES)


if __name__ == "__main__":
    main()
