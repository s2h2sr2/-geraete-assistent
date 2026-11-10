import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from PIL import Image
import io
import urllib.parse

# ─────────────────────────────────────────────────────────────
# KONFIGURATION – nur Gemini API Key nötig (kostenlos!)
# ─────────────────────────────────────────────────────────────

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

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
        "Analysiere das Bild und beantworte folgende Punkte auf Deutsch:\n"
        "1. Um welches Haushaltsgerät handelt es sich?\n"
        "2. Welcher Hersteller und welches genaue Modell ist es "
        "(erkennbar an Aufkleber, Display, Form, Farbe, Knöpfe)?\n"
        "3. Falls Modell nicht eindeutig erkennbar: "
        "Nenne die 2-3 wahrscheinlichsten Modelle.\n\n"
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


def duckduckgo_suche(suchanfrage: str, anzahl: int = 5) -> list[dict]:
    """
    Kostenlose Web-Suche über DuckDuckGo HTML-Seite (kein API-Key nötig).
    Gibt eine Liste mit Titel, Link und Kurztext zurück.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    encoded = urllib.parse.quote_plus(suchanfrage)
    url = f"https://html.duckduckgo.com/html/?q={encoded}&kl=de-de"

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    ergebnisse = []

    for result in soup.select(".result"):
        titel_tag   = result.select_one(".result__title a")
        snippet_tag = result.select_one(".result__snippet")

        if not titel_tag:
            continue

        titel   = titel_tag.get_text(strip=True)
        link    = titel_tag.get("href", "")
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

        # DuckDuckGo-interne Weiterleitungslinks bereinigen
        if link.startswith("//duckduckgo.com/l/?uddg="):
            link_encoded = link.split("uddg=")[-1].split("&")[0]
            link = urllib.parse.unquote(link_encoded)

        if titel and link:
            ergebnisse.append({
                "titel":   titel,
                "link":    link,
                "snippet": snippet,
            })

        if len(ergebnisse) >= anzahl:
            break

    return ergebnisse


def loesung_zusammenfassen(
    geraet_info: str,
    problem: str,
    suchergebnisse: list[dict]
) -> str:
    """Lässt Gemini aus den Suchergebnissen eine strukturierte Lösung erstellen."""
    quellen_text = "\n\n".join([
        f"Quelle {i+1}: {r['titel']}\nURL: {r['link']}\nAuszug: {r['snippet']}"
        for i, r in enumerate(suchergebnisse)
    ])

    prompt = (
        "Du bist ein hilfreicher Reparatur-Assistent für Haushaltsgeräte.\n\n"
        f"**Gerät / Modell:**\n{geraet_info}\n\n"
        f"**Beschriebenes Problem:**\n{problem}\n\n"
        f"**Gefundene Web-Quellen:**\n{quellen_text}\n\n"
        "Erstelle auf Basis dieser Informationen eine klare, "
        "schrittweise Anleitung zur Problemlösung auf Deutsch.\n"
        "- Nummeriere die Schritte.\n"
        "- Weise auf Sicherheitshinweise hin (z. B. Strom ausschalten).\n"
        "- Nenne am Ende die verwendeten Quellen mit URL.\n"
        "- Weise darauf hin, wenn professionelle Hilfe nötig ist."
    )

    response = model.generate_content(prompt)
    return response.text


# ─────────────────────────────────────────────────────────────
# CACHE-FUNKTIONEN (kein extra Paket – nur Session State)
# ─────────────────────────────────────────────────────────────

def cache_schluessel(geraet: str, problem: str) -> str:
    return f"{geraet.strip().lower()}|||{problem.strip().lower()}"

def cache_speichern(schluessel: str, loesung: str, quellen: list[dict]):
    if "lösungs_cache" not in st.session_state:
        st.session_state["lösungs_cache"] = {}
    st.session_state["lösungs_cache"][schluessel] = {
        "loesung": loesung,
        "quellen": quellen,
    }

def cache_laden(schluessel: str) -> dict | None:
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
    "und die KI sucht automatisch die passende Lösung im Web."
)
st.divider()

# ─────────────────────────────────────────────────────────────
# SCHRITT 1: BILD HOCHLADEN & GERÄT ERKENNEN
# ─────────────────────────────────────────────────────────────

st.subheader("📷 Schritt 1: Gerät fotografieren")

uploaded_file = st.file_uploader(
    "Lade ein Foto des Geräts hoch (JPG, PNG, WEBP):",
    type=["jpg", "jpeg", "png", "webp"]
)

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Dein Gerät", use_container_width=True)

    if st.button("🔍 Gerät identifizieren", use_container_width=True):
        with st.spinner("KI analysiert das Bild ..."):
            try:
                ergebnis = geraet_identifizieren(image)
                st.session_state["geraet_ergebnis"] = ergebnis
            except Exception as e:
                st.error(f"Fehler bei der Bildanalyse: {e}")

# Ergebnis persistent anzeigen
if "geraet_ergebnis" in st.session_state:
    st.success("✅ Gerät erkannt!")
    st.subheader("🏷️ Erkanntes Gerät:")
    st.markdown(st.session_state["geraet_ergebnis"])

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

st.divider()

# ─────────────────────────────────────────────────────────────
# SCHRITT 3: LÖSUNG SUCHEN
# ─────────────────────────────────────────────────────────────

st.subheader("🌐 Schritt 3: Lösung im Web suchen")

if st.button("🚀 Lösung suchen", use_container_width=True, type="primary"):
    if "geraet_ergebnis" not in st.session_state:
        st.warning("⚠️ Bitte zuerst ein Bild hochladen und das Gerät identifizieren.")
    elif not problem.strip():
        st.warning("⚠️ Bitte beschreibe zuerst das Problem.")
    else:
        geraet_info = st.session_state["geraet_ergebnis"]
        schluessel  = cache_schluessel(geraet_info, problem)
        gecacht     = cache_laden(schluessel)

        if gecacht:
            # ── Aus Cache laden ──────────────────────────────
            st.info("💾 Diese Lösung wurde bereits gefunden – aus dem Speicher geladen!")
            st.subheader("📋 Lösung (aus Cache):")
            st.markdown(gecacht["loesung"])
            st.subheader("🔗 Verwendete Quellen:")
            for q in gecacht["quellen"]:
                st.markdown(f"- [{q['titel']}]({q['link']})")

        else:
            # ── Neu suchen ───────────────────────────────────
            with st.spinner("🔍 Suche im Web (DuckDuckGo) ..."):
                try:
                    # Kompakten Suchbegriff bauen
                    erste_zeile = geraet_info.splitlines()[0].replace("**Gerät:**", "").strip()
                    suchbegriff = f"{erste_zeile} {problem[:80]} Lösung Reparatur"
                    suchbegriff = " ".join(suchbegriff.split()[:12])

                    suchergebnisse = duckduckgo_suche(suchbegriff)

                    if not suchergebnisse:
                        st.warning(
                            "Keine Ergebnisse gefunden. "
                            "Versuche eine genauere Problembeschreibung."
                        )
                    else:
                        with st.spinner("🤖 KI erstellt Lösung aus den Suchergebnissen ..."):
                            loesung = loesung_zusammenfassen(
                                geraet_info, problem, suchergebnisse
                            )

                        # In Cache speichern
                        cache_speichern(schluessel, loesung, suchergebnisse)

                        st.success("✅ Lösung gefunden!")
                        st.subheader("📋 Deine Schritt-für-Schritt-Lösung:")
                        st.markdown(loesung)

                        st.subheader("🔗 Verwendete Web-Quellen:")
                        for q in suchergebnisse:
                            st.markdown(f"- [{q['titel']}]({q['link']})")

                except Exception as e:
                    st.error(f"Fehler: {e}")

# ─────────────────────────────────────────────────────────────
# GESPEICHERTE LÖSUNGEN
# ─────────────────────────────────────────────────────────────

st.divider()

if st.session_state.get("lösungs_cache"):
    with st.expander("💾 Bereits gespeicherte Lösungen anzeigen"):
        for key, val in st.session_state["lösungs_cache"].items():
            geraet_teil, problem_teil = key.split("|||")
            st.markdown(f"**Gerät:** {geraet_teil}")
            st.markdown(f"**Problem:** {problem_teil}")
            st.markdown(val["loesung"])
            st.divider()

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "🤖 Modell: Google Gemini 1.5 Flash (kostenlos) | "
    "🔍 Suche: DuckDuckGo (kostenlos, kein API-Key) | "
    "Lizenz: Google AI Developer Terms | "
    "Quelle: https://ai.google.dev"
)
