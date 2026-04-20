"""
Work Mentor — Skill Research Engine
Recherchiert echte Skills aus echten Stellenanzeigen + Web-Quellen.
Kein "Wissen", nur Daten.
"""

import json
import os
import asyncio
import httpx
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Oxylabs credentials (from OpenClaw — we use web search + fetch)
OXYLABS_USER = os.getenv("OXYLABS_USER", "")
OXYLABS_PASS = os.getenv("OXYLABS_PASS", "")


async def search_web(query: str, count: int = 10) -> list[dict]:
    """Web-Suche über Oxylabs SERP API."""
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
                for r in data.get("results", [{}])[0].get("content", {}).get("results", {}).get("organic", [])[:count]:
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "description": r.get("desc", ""),
                    })
                return results
        except Exception:
            pass
    return []


async def fetch_page(url: str) -> str:
    """Fetcht eine Webseite und extrahiert Text."""
    async with httpx.AsyncClient(timeout=15.0) as http:
        try:
            resp = await http.post(
                "https://realtime.oxylabs.io/v1/queries",
                auth=(OXYLABS_USER, OXYLABS_PASS),
                json={
                    "source": "universal",
                    "url": url,
                    "parse": True,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("results", [{}])[0].get("content", "")
                # Truncate to avoid token explosion
                if isinstance(content, str):
                    return content[:5000]
                return str(content)[:5000]
        except Exception:
            pass
    return ""


async def research_skills(zieljob: str, branche: str, aktueller_job: str) -> dict:
    """
    Recherchiert Skills für eine Zielposition aus echten Quellen.
    
    Returns:
        {
            "skills": [...],
            "varianz_fragen": [...],  # Rückfragen die sich aus der Varianz ergeben
            "meta": {...}
        }
    """
    
    # SCHRITT 1: Parallele Suchen
    search_tasks = [
        # Stellenanzeigen
        search_web(f"{zieljob} {branche} Stellenanzeige Anforderungen Skills", 10),
        # Erfolgsfaktoren + Scheitergründe  
        search_web(f"{zieljob} {branche} Erfolgsfaktoren Anforderungen Kompetenzen", 10),
        search_web(f"{zieljob} häufigste Fehler scheitern Gründe", 5),
    ]
    
    results = await asyncio.gather(*search_tasks)
    search_stellenanzeigen = results[0]
    search_erfolgsfaktoren = results[1]
    search_scheitergruende = results[2]
    
    # SCHRITT 2: Die besten 5 Seiten im Detail fetchen
    urls_to_fetch = []
    for r in (search_stellenanzeigen + search_erfolgsfaktoren + search_scheitergruende):
        url = r.get("url", "")
        # Nur relevante Seiten fetchen (keine Indeed/Stepstone Listenansichten)
        if url and not any(skip in url for skip in [
            "indeed.com/q-", "stepstone.de/jobs/", "google.com",
            "linkedin.com/jobs", ".pdf"
        ]):
            urls_to_fetch.append(url)
    
    # Maximal 5 Seiten fetchen
    urls_to_fetch = urls_to_fetch[:5]
    
    page_texts = []
    if urls_to_fetch:
        fetch_tasks = [fetch_page(url) for url in urls_to_fetch]
        page_texts = await asyncio.gather(*fetch_tasks)
    
    # SCHRITT 3: Stepstone Übersichtsseite fetchen (hat aggregierte Skill-Daten)
    stepstone_url = f"https://www.stepstone.de/jobs/{zieljob.lower().replace(' ', '-')}-in-{branche.lower().replace(' ', '-')}"
    stepstone_text = await fetch_page(stepstone_url)
    
    # SCHRITT 4: Claude analysiert ALLE echten Daten
    analysis_prompt = f"""
Du bist ein Datenanalyst. Du analysierst ECHTE Daten aus Stellenanzeigen und Web-Quellen.
Du darfst NICHTS dazuerfinden. Nur was in den Daten steht.

## Aufgabe
Analysiere diese Daten für die Zielposition "{zieljob}" in der Branche "{branche}".
Der User ist aktuell "{aktueller_job}".

## Datenquellen

### Stepstone Übersicht (aggregierte Skills)
{stepstone_text[:3000]}

### Suchergebnisse: Stellenanzeigen
{json.dumps(search_stellenanzeigen, ensure_ascii=False, indent=1)[:2000]}

### Suchergebnisse: Erfolgsfaktoren
{json.dumps(search_erfolgsfaktoren, ensure_ascii=False, indent=1)[:2000]}

### Suchergebnisse: Scheitergründe
{json.dumps(search_scheitergruende, ensure_ascii=False, indent=1)[:1000]}

### Detail-Seiten
{chr(10).join([f"--- Seite {i+1} ({urls_to_fetch[i] if i < len(urls_to_fetch) else 'N/A'}) ---{chr(10)}{t[:1500]}" for i, t in enumerate(page_texts)])}

## Was du liefern musst (NUR JSON, kein anderer Text):

{{
  "skills": [
    {{
      "name": "Skill-Name auf Deutsch",
      "kategorie": "hard_skill" | "soft_skill",
      "gewichtung": 0.0-1.0,
      "belege": ["Quelle 1: Zitat oder Fakt", "Quelle 2: ..."],
      "varianz": "hoch" | "mittel" | "niedrig",
      "varianz_erklaerung": "Warum gibt es Unterschiede zwischen den Anzeigen?"
    }}
  ],
  "varianz_fragen": [
    {{
      "frage": "Die Rückfrage an den User",
      "grund": "Warum diese Frage nötig ist",
      "beeinflusst_skills": ["Skill 1", "Skill 2"],
      "optionen": [
        {{"text": "Option A", "skill_anpassung": "Wenn User das wählt, wird Skill X wichtiger"}},
        {{"text": "Option B", "skill_anpassung": "Wenn User das wählt, wird Skill Y wichtiger"}}
      ]
    }}
  ],
  "meta": {{
    "quellen_analysiert": 0,
    "stellenanzeigen_gefunden": 0,
    "vertrauen": "hoch" | "mittel" | "niedrig",
    "vertrauen_grund": "Warum du diesem Ergebnis vertraust oder nicht"
  }}
}}

REGELN:
- 8-10 Skills, sortiert nach Gewichtung (höchste zuerst)
- Gewichtung basiert NUR auf Häufigkeit in den Daten
- "belege" = echte Zitate oder Fakten aus den Quellen
- varianz_fragen: NUR wo es ECHTE Varianz gibt (z.B. "manche Anzeigen sagen Kaltakquise, andere Bestandskunden")
- Wenn keine Varianz → leeres Array
- 0-3 Rückfragen maximal
- NICHTS erfinden. Wenn du es nicht in den Daten findest, nimm es nicht auf.
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": analysis_prompt}]
    )
    
    text = response.content[0].text.strip()
    
    # JSON parsen
    try:
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: JSON aus Text extrahieren
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            result = json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            result = {
                "skills": [],
                "varianz_fragen": [],
                "meta": {"error": "Could not parse analysis", "raw": text[:500]}
            }
    
    return result
