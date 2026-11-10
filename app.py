import streamlit as st
import google.generativeai as genai
import requests
import json
import io
from PIL import Image

# ─────────────────────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────────────────────

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

GOOGLE_SEARCH_API_KEY = st.secrets["GOOGLE_SEARCH_API_KEY"]
GOOGLE_CSE_ID         = st.secrets["GOOGLE_CSE_ID"]

# ─────────────────────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────────────────────

def geraet_identifizieren(image: Image.Image) -> str:
    """Schickt das Bild an Gemini und lässt Gerät + Modell identifizieren."""
    img_bytes = io.BytesIO()
    image.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    prompt = (
        "Du bist ein Experte für Haushaltsgeräte.\n"
        "Analysiere das Bild und beantworte folgende Fragen auf Deutsch:\n"
        "1. Um welches Haushaltsgerät handelt es sich?\n"
        "2. Welcher Hersteller und welches genaue Modell ist es "
        "(falls erkennbar, z. B. an Aufkleber, Display, Form)?\n"
        "3. Falls Modell nicht eindeutig erkennbar: Nenne die wahrscheinlichsten Modelle.\n\n"
        "Antworte strukturiert:\n"
        "**Gerät:** ...\n"
        "**Hersteller:** ...\n"
        "**Modell:** ...\n"
        "**Begründung:** ..."
    )

    response = model.generate_content([
        prompt,
        {"mime_type": "image/png", "data": img_bytes.read()}
    ])
    return response.text


def web_suche(suchanfrage: str) -> list[dict]:
    """Führt eine Google Custom Search durch und gibt Ergebnisse zurück."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_SEARCH_API_KEY,
        "cx":  GOOGLE_CSE_ID,
        "q":   suchanfrage,
        "num": 5,
        "lr":  "lang_de",
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    items = response.json().get("items", [])
    return [
        {
            "titel": item.get("title", ""),
            "link":  item.get("link", ""),
            "snippet": item.get("snippet", ""),
        }
        for item in items
    ]


def loesung_zusammenfassen(geraet_info: str, problem: str, suchergebnisse: list[dict]) -> str:
    """Lässt Gemini aus den Suchergebnissen eine strukturierte Lösung erstellen."""
    quellen_text = "\n\n".join([
        f"Quelle {i+1}: {r['titel']}\nURL: {r['link']}\nAuszug: {r['snippet']}"
        for i, r in enumerate(suchergebnisse)
    ])

    prompt = (
        f"Du bist ein hilfreicher Reparatur-Assistent für Haushaltsgeräte.\n\n"
        f"**Gerät / Modell:** {geraet_info}\n"
        f"**Beschriebenes Problem:** {problem}\n\n"
        f"**Gefundene Web-Quellen:**\n{quellen_text}\n\n"
        "Erstelle auf Basis dieser Quellen eine klare, schrittweise Anleitung zur Problemlösung auf Deutsch. "
        "Nenne am Ende die verwendeten Quellen mit URL. "
        "Weise darauf hin, wenn professionelle Hilfe nötig ist."
    )

    response = model.generate_content(prompt)
    return response.text


def cache_schluessel(geraet: str, problem: str) -> str:
    """Erstellt einen eindeutigen Cache-Schlüssel aus Gerät + Problem."""
    return f"{geraet.strip().lower()}|||{problem.strip().lower()}"


def cache_speichern(schluessel: str, loesung: str, quellen: list[dict]):
    """Speichert eine Lösung im Session-State-Cache."""
    if "lösungs_cache" not in st.session_state:
        st.session_state["lösungs_cache"] = {}
    st.session_state["lösungs_cache"][schluessel] = {
        "loesung": loesung,
        "quellen": quellen,
    }


def cache_laden(schluessel: str) -> dict | None:
    """Lädt eine gecachte Lösung, falls vorhanden."""
    return st.session_state.get("lösungs_cache", {}).get(schluessel, None)

# ─────────────────────────────────────────────────────────────
# SEITEN-KONFIGURATION
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Geräte-Assistent 🔧",
    page_icon="🔧",
    layout="centered"
)

# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────

st.title("🔧 Haushaltsgeräte-Assistent")
st.write(
    "Lade ein Foto deines Haushaltsgeräts hoch, beschreibe das Problem – "
    "und die KI sucht für dich die passende Lösung im Web."
)
st.divider()

# ─────────────────────────────────────────────────────────────
# SCHRITT 1: BILD HOCHLADEN
# ─────────────────────────────────────────────────────────────

st.subheader("📷 Schritt 1: Gerät fotografieren")
uploaded_file = st.file_uploader(
    "Lade ein Foto des Geräts hoch (JPG, PNG, WEBP):",
    type=["jpg", "jpeg", "png", "webp"]
)

geraet_ergebnis = None

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Dein Gerät", use_container_width=True)

    if st.button("🔍 Gerät identifizieren", use_container_width=True):
        with st.spinner("KI analysiert das Bild ..."):
            try:
                geraet_ergebnis = geraet_identifizieren(image)
                st.session_state["geraet_ergebnis"] = geraet_ergebnis
            except Exception as e:
                st.error(f"Fehler bei der Bildanalyse: {e}")

# Ergebnis aus Session State laden (bleibt nach Klick sichtbar)
if "geraet_ergebnis" in st.session_state:
    geraet_ergebnis = st.session_state["geraet_ergebnis"]
    st.success("✅ Gerät erkannt!")
    st.subheader("🏷️ Erkanntes Gerät:")
    st.markdown(geraet_ergebnis)

st.divider()

# ─────────────────────────────────────────────────────────────
# SCHRITT 2: PROBLEM BESCHREIBEN
# ─────────────────────────────────────────────────────────────

st.subheader("🛠️ Schritt 2: Problem beschreiben")

problem = st.text_area(
    "Was ist das Problem mit deinem Gerät?",
    placeholder=(
        "z. B. 'Die Waschmaschine schleudert nicht mehr und zeigt Fehlercode E3 an.'\n"
        "z. B. 'Der Kühlschrank macht komische Geräusche und kühlt nicht mehr richtig.'"
    ),
    height=120
)

# ─────────────────────────────────────────────────────────────
# SCHRITT 3: LÖSUNG SUCHEN
# ─────────────────────────────────────────────────────────────

st.divider()
st.subheader("🌐 Schritt 3: Lösung im Web suchen")

if st.button("🚀 Lösung suchen", use_container_width=True, type="primary"):
    if not geraet_ergebnis:
        st.warning("⚠️ Bitte zuerst ein Bild hochladen und das Gerät identifizieren.")
    elif not problem.strip():
        st.warning("⚠️ Bitte beschreibe zuerst das Problem.")
    else:
        # Cache prüfen – wurde die Lösung schon einmal gesucht?
        schluessel = cache_schluessel(geraet_ergebnis, problem)
        gecacht = cache_laden(schluessel)

        if gecacht:
            st.info("💾 Diese Lösung wurde bereits gefunden – aus dem Speicher geladen!")
            st.subheader("📋 Lösung (aus Cache):")
            st.markdown(gecacht["loesung"])
            st.subheader("🔗 Verwendete Quellen:")
            for q in gecacht["quellen"]:
                st.markdown(f"- [{q['titel']}]({q['link']})")
        else:
            with st.spinner("Suche im Web ..."):
                try:
                    # Suchanfrage dynamisch aus Gerät + Problem bauen
                    suchbegriff = f"{geraet_ergebnis.splitlines()[0]} {problem[:100]} Lösung Reparatur"
                    # Zu langen Suchbegriff kürzen
                    suchbegriff = " ".join(suchbegriff.split()[:15])

                    suchergebnisse = web_suche(suchbegriff)

                    if not suchergebnisse:
                        st.warning("Keine Web-Ergebnisse gefunden. Versuche eine genauere Problembeschreibung.")
                    else:
                        with st.spinner("KI erstellt Lösung aus den Suchergebnissen ..."):
                            loesung = loesung_zusammenfassen(
                                geraet_ergebnis, problem, suchergebnisse
                            )

                        # In Cache speichern
                        cache_speichern(schluessel, loesung, suchergebnisse)

                        st.success("✅ Lösung gefunden!")
                        st.subheader("📋 Deine Schritt-für-Schritt-Lösung:")
                        st.markdown(loesung)

                        st.subheader("🔗 Verwendete Web-Quellen:")
                        for q in suchergebnisse:
                            st.markdown(f"- [{q['titel']}]({q['link']})")

                except requests.exceptions.RequestException as e:
                    st.error(f"Fehler bei der Web-Suche: {e}")
                except Exception as e:
                    st.error(f"Unerwarteter Fehler: {e}")

# ─────────────────────────────────────────────────────────────
# GESPEICHERTE LÖSUNGEN ANZEIGEN
# ─────────────────────────────────────────────────────────────

st.divider()

if st.session_state.get("lösungs_cache"):
    with st.expander("💾 Bereits gespeicherte Lösungen anzeigen"):
        for key, val in st.session_state["lösungs_cache"].items():
            geraet_teil, problem_teil = key.split("|||")
            st.markdown(f"**Gerät:** {geraet_teil}  \n**Problem:** {problem_teil}")
            st.markdown(val["loesung"])
            st.divider()

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.caption(
    "🤖 Modell: Google Gemini 1.5 Flash (vortrainiert) | "
    "🔍 Suche: Google Custom Search API | "
    "Lizenz: Google AI Developer Terms | "
    "Quelle: https://ai.google.dev"
)
