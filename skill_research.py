"""
Work Mentor — Skill Research Engine v2
Recherchiert echte Skills + generiert scharfe Kalibrierungs-Fragen.
"""

import json
import os
import re
import asyncio
import httpx
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

OXYLABS_USER = os.getenv("OXYLABS_USER", "")
OXYLABS_PASS = os.getenv("OXYLABS_PASS", "")


async def search_web(query: str, count: int = 10) -> list[dict]:
    """Web-Suche über Oxylabs oder DuckDuckGo Fallback."""
    if OXYLABS_USER and OXYLABS_PASS:
        async with httpx.AsyncClient(timeout=15.0) as http:
            try:
                resp = await http.post(
                    "https://realtime.oxylabs.io/v1/queries",
                    auth=(OXYLABS_USER, OXYLABS_PASS),
                    json={"source": "google_search", "query": query, "geo_location": "Germany", "locale": "de", "pages": 1, "parse": True},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for r in data.get("results", [{}])[0].get("content", {}).get("results", {}).get("organic", [])[:count]:
                        results.append({"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("desc", "")})
                    return results
            except Exception:
                pass

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        try:
            resp = await http.get("https://html.duckduckgo.com/html/", params={"q": query, "kl": "de-de"},
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"})
            if resp.status_code == 200:
                text = resp.text
                results = []
                snippets = re.findall(r'class="result__snippet">(.*?)</a>', text, re.DOTALL)
                titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', text, re.DOTALL)
                for i in range(min(count, len(titles))):
                    results.append({
                        "title": re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else "",
                        "url": "", "description": re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else "",
                    })
                return results
        except Exception:
            pass
    return []


async def fetch_page(url: str) -> str:
    """Fetcht eine Webseite und extrahiert Text."""
    if OXYLABS_USER and OXYLABS_PASS:
        async with httpx.AsyncClient(timeout=15.0) as http:
            try:
                resp = await http.post("https://realtime.oxylabs.io/v1/queries", auth=(OXYLABS_USER, OXYLABS_PASS),
                    json={"source": "universal", "url": url, "parse": True})
                if resp.status_code == 200:
                    content = resp.json().get("results", [{}])[0].get("content", "")
                    return str(content)[:5000] if content else ""
            except Exception:
                pass

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        try:
            resp = await http.get(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"})
            if resp.status_code == 200:
                text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text[:5000]
        except Exception:
            pass
    return ""


async def research_skills(zieljob: str, branche: str, aktueller_job: str) -> dict:
    """Recherchiert Skills + generiert scharfe Kalibrierungs-Fragen."""

    # SCHRITT 1: Parallele Web-Suchen
    search_tasks = [
        search_web(f"{zieljob} {branche} Stellenanzeige Anforderungen Qualifikation", 10),
        search_web(f"{zieljob} Aufgaben Kompetenzen Skills werden", 10),
        search_web(f"{zieljob} häufigste Fehler scheitern Gründe", 5),
        search_web(f"{zieljob} Arten Typen Unterschiede Spezialisierung", 5),
    ]
    results = await asyncio.gather(*search_tasks)
    all_results = []
    for r in results:
        all_results.extend(r)

    # SCHRITT 2: Karriere-Ratgeber Seiten fetchen
    urls_to_fetch = []
    for r in all_results:
        url = r.get("url", "")
        if url and any(good in url for good in [
            "karrierebibel", "karriereakademie", "karriere.at",
            "salesjob", "kursfinder", "springerprofessional"
        ]):
            urls_to_fetch.append(url)
    page_texts = []
    if urls_to_fetch[:3]:
        page_texts = await asyncio.gather(*[fetch_page(u) for u in urls_to_fetch[:3]])

    # SCHRITT 3: Prüfe Datenlage
    total_content = " ".join([r.get("title","")+" "+r.get("description","") for r in all_results])
    total_content += " ".join([t for t in page_texts if t])
    has_enough_data = len(total_content.strip()) > 500

    # SCHRITT 4: Claude analysiert
    if has_enough_data:
        prompt = build_prompt_with_data(zieljob, branche, aktueller_job, all_results, page_texts, urls_to_fetch)
    else:
        prompt = build_prompt_fallback(zieljob, branche, aktueller_job)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_json_response(response.content[0].text.strip())


def build_prompt_with_data(zieljob, branche, aktueller_job, search_results, page_texts, urls):
    search_data = json.dumps(search_results[:20], ensure_ascii=False, indent=1)[:5000]
    pages_data = "\n".join([f"--- {urls[i] if i<len(urls) else '?'} ---\n{t[:2000]}" for i,t in enumerate(page_texts) if t])

    return f"""Du bist ein Arbeitsmarkt-Experte der Stellenanzeigen analysiert.
Position: "{zieljob}" in "{branche}". User ist aktuell "{aktueller_job}".

## Daten
{search_data}

{pages_data}

## Deine Aufgabe

### 1. Skills (8-10)
Finde die wichtigsten Skills aus den Daten. Sortiert nach Häufigkeit.

### 2. Kalibrierungs-Fragen (WICHTIG — 3-5 Fragen!)

Die Position "{zieljob}" ist NICHT eindeutig. Es gibt verschiedene ARTEN davon.
Zum Beispiel bei "Vertriebsleiter":
- Regionaler VL vs. nationaler VL → komplett andere Skills
- Neukundenakquise vs. Bestandskunden → andere Schwerpunkte
- 5-Personen-Team vs. 50-Personen-Team → andere Führungsanforderungen
- Operativ im Außendienst vs. strategisch im Büro → andere Anforderungen
- Startup/KMU vs. Konzern → andere Kultur, andere Skills

Deine Kalibrierungs-Fragen müssen GENAU DIESE Unterschiede aufklären.
Jede Frage muss die Skill-Gewichtung MESSBAR verändern.

REGELN für Fragen:
- Mindestens 3, maximal 5 Fragen
- Jede Frage hat 2-3 inhaltliche Optionen PLUS eine "Beides" oder "Gemischt" Option
- Die letzte Option ist IMMER eine Ausweichoption ("Beides", "Gemischt", "Kommt drauf an")
- Jede inhaltliche Option ändert welche Skills wie wichtig sind
- Sprache: Du-Form, einfach, keine HR-Fachbegriffe
- Die Fragen sind KEIN Quiz — sie helfen uns die Position zu verstehen

GUTE Fragen (mit Ausweichoption!):
- "Wie groß wäre dein Team?" → 2-10 / 10-30 / 30+ / Weiß ich noch nicht
- "Liegt der Fokus eher auf Neukunden oder Bestandskunden?" → Neukunden / Bestandskunden / Beides gleich wichtig
- "Wärst du viel unterwegs oder eher vom Büro aus?" → Viel unterwegs / Büro / Mix aus beidem
- "Eher operativ oder strategisch?" → Operativ / Strategisch / Beides

SCHLECHTE Fragen:
- "Welche Unternehmensgröße?" → zu generisch, ändert zu wenig
- "Welche Branche?" → wissen wir schon
- Alles was der User schon angegeben hat
- Fragen OHNE Ausweichoption → User fühlt sich in eine Box gedrängt

Antworte NUR mit JSON:
{get_json_template()}
"""


def build_prompt_fallback(zieljob, branche, aktueller_job):
    return f"""Du bist ein Arbeitsmarkt-Experte.
Position: "{zieljob}" in "{branche}". User ist aktuell "{aktueller_job}".

Keine Live-Daten verfügbar. Nutze dein Wissen über ECHTE Stellenanzeigen.

### 1. Skills (8-10)
Was fordern echte Stellenanzeigen für "{zieljob} {branche}"?

### 2. Kalibrierungs-Fragen (3-5 Fragen!)

Die Position "{zieljob}" ist NICHT eindeutig. Es gibt verschiedene TYPEN/ARTEN.
Deine Fragen müssen aufklären WELCHEN TYP der User anstrebt.

Denke daran: Ein {zieljob} bei einem Startup ist komplett anders als bei einem Konzern.
Ein {zieljob} der selbst verkauft ist anders als einer der nur führt.
Ein {zieljob} mit 5 Leuten braucht andere Skills als einer mit 50.

REGELN:
- 3-5 Fragen die die Position SCHÄRFEN
- Du-Form, einfache Sprache
- 2-3 Optionen pro Frage
- Jede Option verändert die Skill-Gewichtung

Antworte NUR mit JSON:
{get_json_template()}
"""


def get_json_template():
    return """{
  "skills": [
    {
      "name": "Skill-Name",
      "kategorie": "hard_skill oder soft_skill",
      "gewichtung": 0.9,
      "belege": ["Quelle/Zitat"],
      "varianz": "hoch oder mittel oder niedrig",
      "varianz_erklaerung": "Warum Varianz"
    }
  ],
  "varianz_fragen": [
    {
      "frage": "Deine Rückfrage an den User (Du-Form)",
      "grund": "Warum diese Frage die Position schärft",
      "beeinflusst_skills": ["Skill 1", "Skill 2"],
      "optionen": [
        {"text": "Option A", "skill_anpassung": "Wie sich Skills ändern"},
        {"text": "Option B", "skill_anpassung": "Wie sich Skills ändern"},
        {"text": "Beides / Gemischt", "skill_anpassung": "Beide Bereiche relevant, breites Profil"}
      ]
    }
  ],
  "meta": {
    "quellen_analysiert": 10,
    "stellenanzeigen_gefunden": 5,
    "vertrauen": "hoch/mittel/niedrig",
    "vertrauen_grund": "Begründung"
  }
}"""


def parse_json_response(text: str) -> dict:
    try:
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
            text = text.strip()
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"skills": [], "varianz_fragen": [], "meta": {"error": "parse_failed", "raw": text[:300]}}
