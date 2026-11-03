"""
Surveille les 2 pages de vente Opening Session Verbier (GitHub Actions).
Deux sessions par jour, lancées par le workflow :
  - session du matin     : démarre ~7h17, tourne jusqu'à 12h30 (heure suisse)
  - session de l'après-midi : démarre ~11h47, tourne jusqu'à 17h30
Vérification toutes les 60 s. Le nom du topic ntfy vient du secret NTFY_TOPIC.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
TEST = os.environ.get("TEST", "").lower() == "true"

PAGES = {
    "Billet seul": "https://verbier4vallees.ch/en/online-shop/activities/opening-session_activity_410650",
    "Billet + train": "https://verbier4vallees.ch/en/online-shop/activities/opening-session-st.nicholas-express_activity_426820",
}

# ====== REGLAGES ======
PAUSE = 60          # secondes entre 2 vérifications
RENOTIF = 180       # secondes mini entre 2 alertes pour une même page
FIN_MATIN = (12, 30)
FIN_APREM = (17, 30)
# ======================

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; verbier-watch)"}
TZ = ZoneInfo("Europe/Zurich")


def maintenant():
    return datetime.now(TZ)


def heure_de_fin(t):
    """Choisit l'heure de fin de session selon l'heure de démarrage."""
    h = t.hour + t.minute / 60
    if 7.0 <= h < 11.5:
        hh, mm = FIN_MATIN
    elif 11.5 <= h < 17.5:
        hh, mm = FIN_APREM
    else:
        return t + timedelta(minutes=15)  # lancement manuel hors horaires : session courte
    return t.replace(hour=hh, minute=mm, second=0, microsecond=0)


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

    fin = heure_de_fin(maintenant())
    print(f"Session démarrée à {maintenant():%H:%M}, fin prévue à {fin:%H:%M} (heure suisse).")

    if TEST:
        notifier("Verbier : test", "Test OK, les notifications fonctionnent.",
                 list(PAGES.values())[0])
        print("Notification de test envoyée.")

    derniere_alerte = {}

    while True:
        for nom, url in PAGES.items():
            try:
                ouvert = est_ouvert(url)
            except Exception as e:
                print(f"[{maintenant():%H:%M:%S}] {nom} : erreur {e}")
                continue

            etat = "OUVERT !" if ouvert else "fermé" if ouvert is False else "page illisible"
            print(f"[{maintenant():%H:%M:%S}] {nom} : {etat}")

            if ouvert is True and time.time() - derniere_alerte.get(nom, 0) >= RENOTIF:
                notifier(f"Verbier 5 CHF : {nom}",
                         f"{nom} : des billets sont en vente ! Fonce.", url)
                derniere_alerte[nom] = time.time()

        sys.stdout.flush()
        if TEST or maintenant() + timedelta(seconds=PAUSE) >= fin:
            break
        time.sleep(PAUSE)

    print("Session terminée.")


if __name__ == "__main__":
    main()
