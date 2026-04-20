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
    """Web-Suche über Oxylabs SERP API oder DuckDuckGo Fallback."""
    
    # Versuche Oxylabs wenn Credentials vorhanden
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
                    for r in data.get("results", [{}])[0].get("content", {}).get("results", {}).get("organic", [])[:count]:
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "description": r.get("desc", ""),
                        })
                    return results
            except Exception:
                pass
    
    # Fallback: DuckDuckGo HTML Suche (kein API Key nötig)
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        try:
            resp = await http.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query, "kl": "de-de"},
                headers={"User-Agent": "Mozilla/5.0 (compatible; WorkMentor/1.0)"}
            )
            if resp.status_code == 200:
                # Einfaches HTML Parsing
                text = resp.text
                results = []
                # Extrahiere Ergebnisse aus DuckDuckGo HTML
                import re
                snippets = re.findall(r'class="result__snippet">(.*?)</a>', text, re.DOTALL)
                titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', text, re.DOTALL)
                urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', text, re.DOTALL)
                
                for i in range(min(count, len(titles))):
                    results.append({
                        "title": re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else "",
                        "url": urls[i].strip() if i < len(urls) else "",
                        "description": re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else "",
                    })
                return results
        except Exception:
            pass
    
    return []


async def fetch_page(url: str) -> str:
    """Fetcht eine Webseite und extrahiert Text."""
    
    # Versuche Oxylabs wenn Credentials vorhanden
    if OXYLABS_USER and OXYLABS_PASS:
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
                    if isinstance(content, str):
                        return content[:5000]
                    return str(content)[:5000]
            except Exception:
                pass
    
    # Fallback: Direkt fetchen
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        try:
            resp = await http.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; WorkMentor/1.0)"}
            )
            if resp.status_code == 200:
                import re
                # HTML Tags entfernen, nur Text
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
    Recherchiert Skills für eine Zielposition aus echten Quellen.
    
    Returns:
        {
            "skills": [...],
            "varianz_fragen": [...],  # Rückfragen die sich aus der Varianz ergeben
            "meta": {...}
        }
    """
    
    # SCHRITT 1: Viele parallele Suchen für breite Datenbasis
    # Die Snippets der Suchergebnisse sind unsere Hauptquelle!
    search_tasks = [
        # Stellenanzeigen (Snippets enthalten oft Anforderungen)
        search_web(f"{zieljob} {branche} Stellenanzeige Anforderungen Qualifikation", 10),
        search_web(f"{zieljob} {branche} Aufgaben Kompetenzen Profil", 10),
        # Karriere-Ratgeber
        search_web(f"{zieljob} werden Anforderungen Stärken Skills", 10),
        search_web(f"{zieljob} Aufgaben Gehalt Karriere", 5),
        # Scheitergründe + Erfolgsfaktoren
        search_web(f"{zieljob} häufigste Fehler scheitern warum", 5),
        search_web(f"{zieljob} Erfolgsfaktoren was macht einen guten", 5),
    ]
    
    results = await asyncio.gather(*search_tasks)
    all_search_results = []
    for result_list in results:
        all_search_results.extend(result_list)
    
    # SCHRITT 2: Nur 2-3 Karriere-Ratgeber Seiten im Detail fetchen
    # (Die haben die besten, strukturierten Infos)
    urls_to_fetch = []
    for r in all_search_results:
        url = r.get("url", "")
        if not url:
            continue
        # Nur Karriere-Ratgeber (nicht Jobbörsen-Listen)
        if any(good in url for good in [
            "karrierebibel.de", "karriereakademie.de", "karriere.at",
            "mein-studium-karriere.de", "salesjob.de", "kursfinder.de",
            "springerprofessional.de", "seismic.com"
        ]):
            urls_to_fetch.append(url)
    
    urls_to_fetch = urls_to_fetch[:3]
    
    page_texts = []
    if urls_to_fetch:
        fetch_tasks = [fetch_page(url) for url in urls_to_fetch]
        page_texts = await asyncio.gather(*fetch_tasks)
    
    # SCHRITT 3: Stepstone Übersichtsseite (aggregierte Skill-Daten im Sidebar)
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

### Alle Suchergebnisse (Stellenanzeigen + Ratgeber + Erfolgsfaktoren)
{json.dumps(all_search_results, ensure_ascii=False, indent=1)[:6000]}

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
