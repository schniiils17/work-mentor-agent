"""
Work Mentor — Skill Research Engine
Recherchiert echte Skills für Zielpositionen.

Strategie:
1. Versuche Web-Recherche (Oxylabs oder DuckDuckGo)
2. Wenn Web-Recherche keine Daten liefert → Claude-Analyse als Fallback
3. Claude darf NUR aus Daten arbeiten, nicht halluzinieren
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
                    json={
                        "source": "google_search",
                        "query": query,
                        "geo_location": "Germany",
                        "locale": "de",
                        "pages": 1,
                        "parse": True,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    organic = data.get("results", [{}])[0].get("content", {}).get("results", {}).get("organic", [])
                    for r in organic[:count]:
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "description": r.get("desc", ""),
                        })
                    return results
            except Exception:
                pass
    
    # Fallback: DuckDuckGo
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        try:
            resp = await http.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query, "kl": "de-de"},
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
            )
            if resp.status_code == 200:
                text = resp.text
                results = []
                snippets = re.findall(r'class="result__snippet">(.*?)</a>', text, re.DOTALL)
                titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', text, re.DOTALL)
                
                for i in range(min(count, len(titles))):
                    results.append({
                        "title": re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else "",
                        "url": "",
                        "description": re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else "",
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
                resp = await http.post(
                    "https://realtime.oxylabs.io/v1/queries",
                    auth=(OXYLABS_USER, OXYLABS_PASS),
                    json={"source": "universal", "url": url, "parse": True},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("results", [{}])[0].get("content", "")
                    if isinstance(content, str):
                        return content[:5000]
                    return str(content)[:5000]
            except Exception:
                pass
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        try:
            resp = await http.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
            )
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
    """
    Recherchiert Skills für eine Zielposition.
    Versucht Web-Recherche, fällt auf Claude zurück.
    """
    
    # SCHRITT 1: Parallele Web-Suchen
    search_tasks = [
        search_web(f"{zieljob} {branche} Stellenanzeige Anforderungen Qualifikation", 10),
        search_web(f"{zieljob} Aufgaben Kompetenzen Skills werden", 10),
        search_web(f"{zieljob} häufigste Fehler scheitern Gründe", 5),
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
        fetch_tasks = [fetch_page(url) for url in urls_to_fetch[:3]]
        page_texts = await asyncio.gather(*fetch_tasks)
    
    # SCHRITT 3: Prüfe ob wir genug Daten haben
    total_content = ""
    for r in all_results:
        total_content += r.get("title", "") + " " + r.get("description", "") + " "
    for t in page_texts:
        total_content += t + " "
    
    has_enough_data = len(total_content.strip()) > 500
    
    # SCHRITT 4: Claude analysiert
    if has_enough_data:
        # Web-Daten vorhanden → Claude analysiert echte Daten
        analysis_prompt = build_analysis_prompt_with_data(
            zieljob, branche, aktueller_job, all_results, page_texts, urls_to_fetch
        )
    else:
        # Keine Web-Daten → Claude nutzt Trainings-Wissen (mit Disclaimer)
        analysis_prompt = build_analysis_prompt_fallback(zieljob, branche, aktueller_job)
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": analysis_prompt}]
    )
    
    text = response.content[0].text.strip()
    return parse_json_response(text)


def build_analysis_prompt_with_data(zieljob, branche, aktueller_job, search_results, page_texts, urls):
    """Prompt wenn echte Web-Daten vorhanden sind."""
    
    search_data = json.dumps(search_results[:20], ensure_ascii=False, indent=1)[:5000]
    pages_data = "\n".join([
        f"--- Seite: {urls[i] if i < len(urls) else 'N/A'} ---\n{t[:2000]}"
        for i, t in enumerate(page_texts) if t
    ])
    
    return f"""Du bist ein Arbeitsmarkt-Datenanalyst.
Analysiere diese ECHTEN Daten für "{zieljob}" in "{branche}" (aktuell: {aktueller_job}).

## Suchergebnisse
{search_data}

## Detail-Seiten
{pages_data}

## Aufgabe
Erstelle ein Skill-Profil basierend NUR auf diesen Daten.

Antworte NUR mit JSON (kein anderer Text):
{get_json_template()}

REGELN:
- 8-10 Skills, sortiert nach Gewichtung
- Gewichtung basiert auf Häufigkeit in den Daten
- "belege" = echte Zitate aus den Quellen oben
- varianz_fragen: NUR wo echte Varianz existiert
- 0-3 Rückfragen maximal
- NICHTS erfinden was nicht in den Daten steht
"""


def build_analysis_prompt_fallback(zieljob, branche, aktueller_job):
    """Prompt wenn keine Web-Daten verfügbar sind."""
    
    return f"""Du bist ein Arbeitsmarkt-Analyst mit Expertise in Stellenanzeigen.
Analysiere die Position "{zieljob}" in "{branche}" (User aktuell: {aktueller_job}).

Da keine Live-Daten verfügbar sind, nutze dein Wissen über ECHTE Stellenanzeigen:
- Was fordern Stellenanzeigen für "{zieljob} {branche}" typischerweise?
- Welche Skills sind Standard, welche variieren?
- Wo unterscheiden sich die Anforderungen je nach Unternehmensgröße/Art?

Antworte NUR mit JSON (kein anderer Text):
{get_json_template()}

REGELN:
- 8-10 Skills basierend auf TYPISCHEN Stellenanzeigen
- Sei ehrlich über die Varianz (wo Anzeigen sich unterscheiden)
- varianz_fragen: Fragen die klären WIE GENAU der Zieljob aussieht
- Setze meta.vertrauen auf "mittel" (kein Live-Daten)
"""


def get_json_template():
    """JSON Template für die Analyse."""
    return """{
  "skills": [
    {
      "name": "Skill-Name auf Deutsch",
      "kategorie": "hard_skill oder soft_skill",
      "gewichtung": 0.9,
      "belege": ["Typische Formulierung aus Stellenanzeigen"],
      "varianz": "hoch oder mittel oder niedrig",
      "varianz_erklaerung": "Warum Unterschiede zwischen Anzeigen"
    }
  ],
  "varianz_fragen": [
    {
      "frage": "Rückfrage an den User",
      "grund": "Warum nötig",
      "beeinflusst_skills": ["Skill 1", "Skill 2"],
      "optionen": [
        {"text": "Option A", "skill_anpassung": "Effekt auf Skills"},
        {"text": "Option B", "skill_anpassung": "Effekt auf Skills"}
      ]
    }
  ],
  "meta": {
    "quellen_analysiert": 10,
    "stellenanzeigen_gefunden": 5,
    "vertrauen": "hoch oder mittel oder niedrig",
    "vertrauen_grund": "Begründung"
  }
}"""


def parse_json_response(text: str) -> dict:
    """Parst JSON aus der Claude-Antwort."""
    try:
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {
                "skills": [],
                "varianz_fragen": [],
                "meta": {"error": "parse_failed", "raw": text[:300]}
            }
