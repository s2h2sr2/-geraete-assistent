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
model = genai.GenerativeModel("gemini-3.8-flash")

# ─────────────────────────────────────────────────────────────
# SEITEN-KONFIGURATION
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Easy-Fix",
    page_icon="🔧",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Arvo:wght@400;700&family=Pacifico&display=swap');

html, body, [class*="css"] {
    font-family: 'Arvo', serif !important;
    background-color: #EFF5FF !important;
    color: #1a1a2e !important;
}

.easy-fix-title {
    font-family: 'Pacifico', cursive !important;
    font-size: 3.2rem !important;
    color: #FF914D !important;
    text-align: center;
    letter-spacing: 2px;
    margin-bottom: 0.2rem;
}

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

.upload-box {
    background-color: white;
    border-radius: 14px;
    padding: 2rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    border: 2px solid #C3D8FF;
    margin-top: 1rem;
    font-family: 'Arvo', serif;
}

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

hr {
    border-color: #C3D8FF !important;
}

textarea, input {
    font-family: 'Arvo', serif !important;
    border-radius: 8px !important;
}

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
        "**Gerät:** ...\n**Hersteller:** ...\n**Modell:** ...\n**Begründung:** ..."
    )
    response = model.generate_content([
        prompt,
        {"mime_type": "image/png", "data": img_bytes.read()}
    ])
    return response.text


def duckduckgo_suche(suchanfrage: str, anzahl: int = 5) -> list[dict]:
    headers = {"User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )}
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


def loesung_fuer_frage(frage: str) -> str:
    prompt = (
        "Du bist ein hilfreicher Reparatur-Assistent für Haushaltsgeräte.\n\n"
        f"Jemand hat folgendes Problem mit einem Haushaltsgerät:\n'{frage}'\n\n"
        "Erstelle eine klare, schrittweise Anleitung zur Problemlösung auf Deutsch.\n"
        "- Nummeriere die Schritte.\n"
        "- Weise auf Sicherheitshinweise hin (z.B. Strom ausschalten).\n"
        "- Weise darauf hin, wenn professionelle Hilfe nötig ist.\n"
        "- Halte die Antwort verständlich und praktisch."
    )
    response = model.generate_content(prompt)
    return response.text


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

defaults = {
    "ansicht": "home",
    "zuletzt_gesucht": [],
    "upload_modal_offen": False,
    "geraet_ergebnis": None,
    "aktive_frage": None,
    "frage_loesung": None,
    "problem_input_wert": "",
    "oft_gefragt": [
        "Waschmaschine schleudert nicht",
        "Kühlschrank kühlt nicht mehr richtig",
        "Spülmaschine läuft nicht ab",
    ],
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="easy-fix-title">Easy-Fix</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 👤 Navigation")
    if st.button("Profil"):
        st.session_state["ansicht"] = "profil"
        st.session_state["upload_modal_offen"] = False
    if st.button("Historie"):
        st.session_state["ansicht"] = "historie"
        st.session_state["upload_modal_offen"] = False
    if st.button("Einstellungen"):
        st.session_state["ansicht"] = "einstellungen"
        st.session_state["upload_modal_offen"] = False

    st.markdown("---")
    st.markdown("### 🔥 Oft gefragt")
    for frage in st.session_state["oft_gefragt"]:
        st.markdown(f'<span class="tag">❓ {frage}</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🕐 Zuletzt gesucht")
    if st.session_state["zuletzt_gesucht"]:
        for eintrag in reversed(st.session_state["zuletzt_gesucht"][-5:]):
            st.markdown(f'<span class="tag">🔍 {eintrag}</span>', unsafe_allow_html=True)
    else:
        st.caption("Noch keine Suchen.")


# ─────────────────────────────────────────────────────────────
# HAUPTBEREICH
# ─────────────────────────────────────────────────────────────

st.markdown('<div class="easy-fix-title">Easy-Fix 🔧</div>', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center; font-family: Arvo, serif; color:#555; margin-bottom:0.5rem;">'
    'Fotografiere dein Gerät – die KI findet die Lösung.</p>',
    unsafe_allow_html=True
)
st.markdown("---")

ansicht = st.session_state.get("ansicht", "home")

# ── PROFIL ──────────────────────────────────────────────────
if ansicht == "profil":
    st.markdown("## 👤 Profil")
    st.markdown(
        '<div class="card"><h4>Dein Profil</h4>'
        '<p>Hier könnten deine gespeicherten Geräte erscheinen.</p></div>',
        unsafe_allow_html=True
    )
    if st.button("← Zurück"):
        st.session_state["ansicht"] = "home"

# ── HISTORIE ────────────────────────────────────────────────
elif ansicht == "historie":
    st.markdown("## 🕐 Suchverlauf")
    if st.session_state.get("lösungs_cache"):
        for key, val in st.session_state["lösungs_cache"].items():
            geraet_teil, problem_teil = key.split("|||")
            st.markdown(
                f'<div class="card"><h4>🔧 {geraet_teil.title()}</h4>'
                f'<p><b>Problem:</b> {problem_teil}</p></div>',
                unsafe_allow_html=True
            )
            with st.expander("Lösung anzeigen"):
                st.markdown(val["loesung"])
    else:
        st.info("Noch keine gespeicherten Lösungen.")
    if st.button("← Zurück"):
        st.session_state["ansicht"] = "home"

# ── EINSTELLUNGEN ────────────────────────────────────────────
elif ansicht == "einstellungen":
    st.markdown("## ⚙️ Einstellungen")
    if st.button("🗑️ Alle gespeicherten Lösungen löschen"):
        st.session_state["lösungs_cache"] = {}
        st.session_state["zuletzt_gesucht"] = []
        st.success("Cache geleert!")
    if st.button("← Zurück"):
        st.session_state["ansicht"] = "home"

# ── HAUPTSEITE ───────────────────────────────────────────────
else:
    col_links, col_rechts = st.columns([1, 2], gap="large")

    # ══════════════════════════════════════════════
    # LINKE SPALTE – Oft gefragt + Upload-Button
    # ══════════════════════════════════════════════
    with col_links:
        st.markdown("### 🔥 Oft gefragt")

        for frage in st.session_state["oft_gefragt"]:
            if st.button(f"❓ {frage}", key=f"frage_{frage}", use_container_width=True):
                st.session_state["aktive_frage"] = frage
                st.session_state["frage_loesung"] = None
                st.session_state["upload_modal_offen"] = False

        st.markdown("---")

        if st.button("📷 Foto hochladen & Problem beschreiben", use_container_width=True):
            st.session_state["upload_modal_offen"] = not st.session_state["upload_modal_offen"]
            st.session_state["aktive_frage"] = None
            st.session_state["frage_loesung"] = None

    # ══════════════════════════════════════════════
    # RECHTE SPALTE – Ergebnisse / Upload
    # ══════════════════════════════════════════════
    with col_rechts:

        # ── FALL 1: Upload-Bereich ist offen ──────
        if st.session_state["upload_modal_offen"]:
            st.markdown("### 📷 Gerät fotografieren & Problem beschreiben")

            uploaded_file = st.file_uploader(
                "Lade ein Foto deines Geräts hoch (JPG, PNG, WEBP):",
                type=["jpg", "jpeg", "png", "webp"],
                key="foto_upload"
            )

            # Textfeld – Wert wird sofort in session_state gespeichert
            def problem_geaendert():
                st.session_state["problem_input_wert"] = st.session_state["problem_input"]

            st.text_area(
                "Was ist das Problem?",
                placeholder=(
                    "z. B. 'Die Waschmaschine schleudert nicht mehr und zeigt E3 an.'\n"
                    "z. B. 'Der Kühlschrank macht Geräusche und kühlt nicht.'"
                ),
                height=110,
                key="problem_input",
                value=st.session_state["problem_input_wert"],
                on_change=problem_geaendert
            )

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                analyse_btn = st.button(
                    "🔍 Gerät erkennen & Lösung suchen",
                    use_container_width=True,
                    type="primary"
                )
            with col_btn2:
                if st.button("✖ Schließen", use_container_width=True):
                    st.session_state["upload_modal_offen"] = False
                    st.session_state["problem_input_wert"] = ""
                    st.rerun()

            if analyse_btn:
                problem_text = st.session_state["problem_input_wert"]
                if not uploaded_file:
                    st.warning("⚠️ Bitte zuerst ein Foto hochladen.")
                elif not problem_text.strip():
                    st.warning("⚠️ Bitte das Problem beschreiben.")
                else:
                    image = Image.open(uploaded_file)
                    st.image(image, caption="Dein Gerät", use_container_width=True)

                    with st.spinner("🔍 KI analysiert das Bild ..."):
                        try:
                            geraet_info = geraet_identifizieren(image)
                            st.session_state["geraet_ergebnis"] = geraet_info
                        except Exception as e:
                            st.error(f"Fehler bei der Bildanalyse: {e}")
                            st.stop()

                    st.success("✅ Gerät erkannt!")
                    st.markdown("### 🏷️ Das Modell ist")
                    st.markdown(
                        f'<div class="card">{geraet_info}</div>',
                        unsafe_allow_html=True
                    )

                    kurz = problem_text[:40] + ("..." if len(problem_text) > 40 else "")
                    if kurz not in st.session_state["zuletzt_gesucht"]:
                        st.session_state["zuletzt_gesucht"].append(kurz)

                    schluessel = cache_schluessel(geraet_info, problem_text)
                    gecacht    = cache_laden(schluessel)

                    if gecacht:
                        st.info("💾 Aus dem Speicher geladen!")
                        st.markdown("### 🛠️ Hier ist wie du es reparierst:")
                        st.markdown(gecacht["loesung"])
                        st.markdown("### 🔗 Quellen:")
                        for q in gecacht["quellen"]:
                            st.markdown(f"- [{q['titel']}]({q['link']})")
                    else:
                        with st.spinner("🌐 Suche im Web (DuckDuckGo) ..."):
                            try:
                                erste_zeile = geraet_info.splitlines()[0].replace("**Gerät:**", "").strip()
                                suchbegriff = f"{erste_zeile} {problem_text[:80]} Lösung Reparatur"
                                suchbegriff = " ".join(suchbegriff.split()[:12])
                                suchergebnisse = duckduckgo_suche(suchbegriff)
                            except Exception as e:
                                st.error(f"Fehler bei der Websuche: {e}")
                                st.stop()

                        if not suchergebnisse:
                            st.warning("Keine Ergebnisse. Versuche eine genauere Beschreibung.")
                        else:
                            with st.spinner("🤖 KI erstellt Schritt-für-Schritt-Lösung ..."):
                                loesung = loesung_zusammenfassen(
                                    geraet_info, problem_text, suchergebnisse
                                )
                            cache_speichern(schluessel, loesung, suchergebnisse)
                            st.success("✅ Lösung gefunden!")
                            st.markdown("### 🛠️ Hier ist wie du es reparierst:")
                            st.markdown(loesung)
                            st.markdown("### 🔗 Verwendete Web-Quellen:")
                            for q in suchergebnisse:
                                st.markdown(f"- [{q['titel']}]({q['link']})")

        # ── FALL 2: Oft-gefragt Frage wurde geklickt ──
        elif st.session_state["aktive_frage"]:
            frage = st.session_state["aktive_frage"]
            st.markdown(f"### ❓ {frage}")
            st.markdown("---")

            if st.session_state["frage_loesung"] is None:
                with st.spinner("🤖 KI sucht Lösung ..."):
                    try:
                        loesung = loesung_fuer_frage(frage)
                        st.session_state["frage_loesung"] = loesung
                    except Exception as e:
                        st.error(f"Fehler: {e}")
                        st.stop()

            if st.session_state["frage_loesung"]:
                st.markdown("### 🛠️ Hier ist wie du es reparierst:")
                st.markdown(
                    f'<div class="card">{st.session_state["frage_loesung"]}</div>',
                    unsafe_allow_html=True
                )

            if st.button("← Zurück zur Übersicht"):
                st.session_state["aktive_frage"] = None
                st.session_state["frage_loesung"] = None
                st.rerun()

        # ── FALL 3: Startansicht ──────────────────────
        else:
            st.markdown(
                '<div class="card">'
                '<h4>👋 Willkommen bei Easy-Fix!</h4>'
                '<p>Wähle links eine häufig gestellte Frage aus – '
                'oder lade ein Foto deines Geräts hoch, '
                'um eine persönliche Lösung zu erhalten.</p>'
                '</div>',
                unsafe_allow_html=True
            )


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
