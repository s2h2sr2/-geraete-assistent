import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from PIL import Image
import io
import urllib.parse

# ─────────────────────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────────────────────

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

# ─────────────────────────────────────────────────────────────
# SEITEN-KONFIGURATION
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Easy-Fix",
    page_icon="🔧",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS – Fonts & Farben
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Google Fonts laden ── */
@import url('https://fonts.googleapis.com/css2?family=Arvo:wght@400;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Xuong&display=swap');

/* Fallback falls Xuong nicht bei Google Fonts: nutze einen dekorativen Font */
/* Falls Xuong nicht lädt, wird Arvo als Fallback genutzt */

/* ── Globale Einstellungen ── */
html, body, [class*="css"] {
    font-family: 'Arvo', serif !important;
    background-color: #EFF5FF !important;
    color: #1a1a2e !important;
}

/* ── Haupttitel Easy-Fix ── */
.easy-fix-title {
    font-family: 'Xuong', 'Arvo', serif !important;
    font-size: 3rem !important;
    color: #FF914D !important;
    text-align: center;
    letter-spacing: 2px;
    margin-bottom: 0.2rem;
    text-shadow: 1px 1px 3px rgba(0,0,0,0.1);
}

/* ── Sidebar Styling ── */
[data-testid="stSidebar"] {
    background-color: #C3D8FF !important;
    padding: 1.5rem 1rem;
}

[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'Arvo', serif !important;
    color: #FF914D !important;
}

[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background-color: #FF914D !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Arvo', serif !important;
    font-weight: 700 !important;
    margin-bottom: 0.4rem;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #e07a35 !important;
}

/* ── Sidebar Nav-Links ── */
.nav-item {
    display: block;
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.3rem;
    border-radius: 8px;
    color: #1a1a2e !important;
    font-family: 'Arvo', serif;
    font-weight: 700;
    cursor: pointer;
    background-color: rgba(255,255,255,0.4);
    text-decoration: none;
}

.nav-item:hover {
    background-color: rgba(255, 145, 77, 0.2);
}

/* ── Karten / Boxen ── */
.card {
    background-color: white;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 4px solid #FF914D;
    font-family: 'Arvo', serif;
}

.card h4 {
    color: #FF914D;
    margin-top: 0;
}

/* ── Buttons Hauptbereich ── */
.stButton > button {
    background-color: #FF914D !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Arvo', serif !important;
    font-weight: 700 !important;
    padding: 0.5rem 1.5rem !important;
}

.stButton > button:hover {
    background-color: #e07a35 !important;
}

/* ── Trennlinie ── */
hr {
    border-color: #C3D8FF !important;
}

/* ── Zuletzt gesucht Tags ── */
.tag {
    display: inline-block;
    background-color: #EFF5FF;
    border: 1.5px solid #C3D8FF;
    border-radius: 20px;
    padding: 0.2rem 0.8rem;
    margin: 0.2rem;
    font-size: 0.85rem;
    font-family: 'Arvo', serif;
    color: #1a1a2e;
}

/* ── Upload-Bereich ── */
[data-testid="stFileUploader"] {
    border: 2px dashed #C3D8FF !important;
    border-radius: 10px !important;
    background-color: white !important;
}

/* ── Textareas & Inputs ── */
textarea, input {
    font-family: 'Arvo', serif !important;
    border-radius: 8px !important;
}

/* ── Success / Warning / Error Boxen ── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-family: 'Arvo', serif !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────────────────────

def geraet_identifizieren(image: Image.Image) -> str:
    img_bytes = io.BytesIO()
    image.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    prompt = (
        "Du bist ein Experte für Haushaltsgeräte.\n"
        "Analysiere das Bild und beantworte folgende Punkte auf Deutsch:\n"
        "1. Um welches Haushaltsgerät handelt es sich?\n"
        "2. Welcher Hersteller und welches genaue Modell ist es?\n"
        "3. Falls Modell nicht eindeutig erkennbar: Nenne die 2-3 wahrscheinlichsten Modelle.\n\n"
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
        if link.startswith("//duckduckgo.com/l/?uddg="):
            link_encoded = link.split("uddg=")[-1].split("&")[0]
            link = urllib.parse.unquote(link_encoded)
        if titel and link:
            ergebnisse.append({"titel": titel, "link": link, "snippet": snippet})
        if len(ergebnisse) >= anzahl:
            break

    return ergebnisse


def loesung_zusammenfassen(geraet_info: str, problem: str, suchergebnisse: list[dict]) -> str:
    quellen_text = "\n\n".join([
        f"Quelle {i+1}: {r['titel']}\nURL: {r['link']}\nAuszug: {r['snippet']}"
        for i, r in enumerate(suchergebnisse)
    ])
    prompt = (
        "Du bist ein hilfreicher Reparatur-Assistent für Haushaltsgeräte.\n\n"
        f"**Gerät / Modell:**\n{geraet_info}\n\n"
        f"**Beschriebenes Problem:**\n{problem}\n\n"
        f"**Gefundene Web-Quellen:**\n{quellen_text}\n\n"
        "Erstelle eine klare, schrittweise Anleitung zur Problemlösung auf Deutsch.\n"
        "- Nummeriere die Schritte.\n"
        "- Weise auf Sicherheitshinweise hin.\n"
        "- Nenne am Ende die verwendeten Quellen mit URL.\n"
        "- Weise darauf hin, wenn professionelle Hilfe nötig ist."
    )
    response = model.generate_content(prompt)
    return response.text


def cache_schluessel(geraet: str, problem: str) -> str:
    return f"{geraet.strip().lower()}|||{problem.strip().lower()}"

def cache_speichern(schluessel: str, loesung: str, quellen: list[dict]):
    if "lösungs_cache" not in st.session_state:
        st.session_state["lösungs_cache"] = {}
    st.session_state["lösungs_cache"][schluessel] = {"loesung": loesung, "quellen": quellen}

def cache_laden(schluessel: str) -> dict | None:
    return st.session_state.get("lösungs_cache", {}).get(schluessel, None)


# ─────────────────────────────────────────────────────────────
# SESSION STATE INITIALISIERUNG
# ─────────────────────────────────────────────────────────────

if "ansicht" not in st.session_state:
    st.session_state["ansicht"] = "home"
if "zuletzt_gesucht" not in st.session_state:
    st.session_state["zuletzt_gesucht"] = []
if "oft_gefragt" not in st.session_state:
    st.session_state["oft_gefragt"] = [
        "Waschmaschine schleudert nicht",
        "Kühlschrank kühlt nicht",
        "Spülmaschine läuft nicht ab",
    ]


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="easy-fix-title">Easy-Fix</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Navigation
    st.markdown("### 👤 Navigation")
    if st.button("Profil"):
        st.session_state["ansicht"] = "profil"
    if st.button("Historie"):
        st.session_state["ansicht"] = "historie"
    if st.button("Einstellungen"):
        st.session_state["ansicht"] = "einstellungen"

    st.markdown("---")

    # Oft gefragt
    st.markdown("### 🔥 Oft gefragt")
    for frage in st.session_state["oft_gefragt"]:
        st.markdown(f'<span class="tag">❓ {frage}</span>', unsafe_allow_html=True)

    st.markdown("---")

    # Zuletzt gesucht
    st.markdown("### 🕐 Zuletzt gesucht")
    if st.session_state["zuletzt_gesucht"]:
        for eintrag in reversed(st.session_state["zuletzt_gesucht"][-5:]):
            st.markdown(f'<span class="tag">🔍 {eintrag}</span>', unsafe_allow_html=True)
    else:
        st.caption("Noch keine Suchen.")

    st.markdown("---")

    # Datei-Upload in Sidebar
    st.markdown("### 📁 Medien")
    uploaded_file = st.file_uploader(
        "Foto / Datei hochladen",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed"
    )
    if uploaded_file:
        st.session_state["uploaded_file"] = uploaded_file
        st.success("✅ Datei geladen!")


# ─────────────────────────────────────────────────────────────
# HAUPTBEREICH
# ─────────────────────────────────────────────────────────────

# Titel oben mittig
st.markdown('<div class="easy-fix-title">Easy-Fix 🔧</div>', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center; font-family: Arvo, serif; color:#555;">'
    'Fotografiere dein Gerät – die KI findet die Lösung.</p>',
    unsafe_allow_html=True
)
st.markdown("---")

ansicht = st.session_state.get("ansicht", "home")

# ── PROFIL ──────────────────────────────────────────────────
if ansicht == "profil":
    st.markdown("## 👤 Profil")
    st.markdown('<div class="card"><h4>Dein Profil</h4><p>Hier könnten deine gespeicherten Geräte und Einstellungen erscheinen.</p></div>', unsafe_allow_html=True)
    if st.button("← Zurück"):
        st.session_state["ansicht"] = "home"

# ── HISTORIE ────────────────────────────────────────────────
elif ansicht == "historie":
    st.markdown("## 🕐 Suchverlauf")
    if st.session_state.get("lösungs_cache"):
        for key, val in st.session_state["lösungs_cache"].items():
            geraet_teil, problem_teil = key.split("|||")
            st.markdown(f'<div class="card"><h4>🔧 {geraet_teil.title()}</h4><p><b>Problem:</b> {problem_teil}</p></div>', unsafe_allow_html=True)
            with st.expander("Lösung anzeigen"):
                st.markdown(val["loesung"])
    else:
        st.info("Noch keine gespeicherten Lösungen.")
    if st.button("← Zurück"):
        st.session_state["ansicht"] = "home"

# ── EINSTELLUNGEN ────────────────────────────────────────────
elif ansicht == "einstellungen":
    st.markdown("## ⚙️ Einstellungen")
    st.markdown('<div class="card"><h4>Cache leeren</h4></div>', unsafe_allow_html=True)
    if st.button("🗑️ Alle gespeicherten Lösungen löschen"):
        st.session_state["lösungs_cache"] = {}
        st.session_state["zuletzt_gesucht"] = []
        st.success("Cache geleert!")
    if st.button("← Zurück"):
        st.session_state["ansicht"] = "home"

# ── HAUPTSEITE ───────────────────────────────────────────────
else:
    # Spalten: Linke Spalte (Oft gefragt groß) | Rechte Spalte (Hauptfunktion)
    col_links, col_rechts = st.columns([1, 2], gap="large")

    # ── LINKE SPALTE: Oft gefragt ──
    with col_links:
        st.markdown("### 🔥 Oft gefragt")
        for frage in st.session_state["oft_gefragt"]:
            st.markdown(f'<div class="card"><h4>❓</h4><p>{frage}</p></div>', unsafe_allow_html=True)

    # ── RECHTE SPALTE: Gerät erkennen & Lösung suchen ──
    with col_rechts:

        # Bild aus Sidebar übernehmen
        if "uploaded_file" in st.session_state and st.session_state["uploaded_file"]:
            uploaded_file = st.session_state["uploaded_file"]
            image = Image.open(uploaded_file)
            st.image(image, caption="Dein Gerät", use_container_width=True)

            if st.button("🔍 Gerät identifizieren", use_container_width=True):
                with st.spinner("KI analysiert das Bild ..."):
                    try:
                        ergebnis = geraet_identifizieren(image)
                        st.session_state["geraet_ergebnis"] = ergebnis
                    except Exception as e:
                        st.error(f"Fehler bei der Bildanalyse: {e}")
        else:
            st.markdown(
                '<div class="card"><h4>📷 Foto hochladen</h4>'
                '<p>Lade links in der Seitenleiste ein Foto deines Geräts hoch.</p></div>',
                unsafe_allow_html=True
            )

        # Gerät erkannt anzeigen
        if "geraet_ergebnis" in st.session_state:
            st.markdown("---")
            st.markdown("### 🏷️ Das Modell ist")
            st.markdown(
                f'<div class="card">{st.session_state["geraet_ergebnis"]}</div>',
                unsafe_allow_html=True
            )

            st.markdown("### 🛠️ Hier ist wie du es reparierst:")

            problem = st.text_area(
                "Problem beschreiben:",
                placeholder="z. B. 'Schleudert nicht mehr und zeigt Fehlercode E3 an.'",
                height=100
            )

            if st.button("🚀 Lösung suchen", use_container_width=True, type="primary"):
                if not problem.strip():
                    st.warning("⚠️ Bitte beschreibe zuerst das Problem.")
                else:
                    geraet_info = st.session_state["geraet_ergebnis"]
                    schluessel  = cache_schluessel(geraet_info, problem)
                    gecacht     = cache_laden(schluessel)

                    # Zu zuletzt gesucht hinzufügen
                    kurz = problem[:40] + ("..." if len(problem) > 40 else "")
                    if kurz not in st.session_state["zuletzt_gesucht"]:
                        st.session_state["zuletzt_gesucht"].append(kurz)

                    if gecacht:
                        st.info("💾 Aus dem Speicher geladen!")
                        st.markdown(gecacht["loesung"])
                        st.markdown("### 🔗 Quellen:")
                        for q in gecacht["quellen"]:
                            st.markdown(f"- [{q['titel']}]({q['link']})")
                    else:
                        with st.spinner("🔍 Suche im Web ..."):
                            try:
                                erste_zeile = geraet_info.splitlines()[0].replace("**Gerät:**", "").strip()
                                suchbegriff = f"{erste_zeile} {problem[:80]} Lösung Reparatur"
                                suchbegriff = " ".join(suchbegriff.split()[:12])
                                suchergebnisse = duckduckgo_suche(suchbegriff)

                                if not suchergebnisse:
                                    st.warning("Keine Ergebnisse. Versuche eine genauere Beschreibung.")
                                else:
                                    with st.spinner("🤖 KI erstellt Lösung ..."):
                                        loesung = loesung_zusammenfassen(geraet_info, problem, suchergebnisse)

                                    cache_speichern(schluessel, loesung, suchergebnisse)

                                    st.success("✅ Lösung gefunden!")
                                    st.markdown(
                                        f'<div class="card">{loesung}</div>',
                                        unsafe_allow_html=True
                                    )

                                    st.markdown("### 🔗 Verwendete Web-Quellen:")
                                    for q in suchergebnisse:
                                        st.markdown(f"- [{q['titel']}]({q['link']})")

                            except Exception as e:
                                st.error(f"Fehler: {e}")

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    '<p style="text-align:center; font-size:0.75rem; color:#888; font-family: Arvo, serif;">'
    '🤖 Gemini 2.0 Flash | 🔍 DuckDuckGo | '
    '<a href="https://ai.google.dev" style="color:#FF914D;">ai.google.dev</a></p>',
    unsafe_allow_html=True
)
