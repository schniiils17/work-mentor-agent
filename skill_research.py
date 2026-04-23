"""
Work Mentor — Skill Research Engine v3
Echte Stellenanzeigen via Jooble API → Claude Analyse → Scharfe Kalibrierung
"""

import json
import os
import re
import asyncio
import httpx
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY", "")


async def fetch_jooble_jobs(zieljob: str, branche: str, count: int = 50) -> list[dict]:
    """Holt echte Stellenanzeigen von Jooble API."""
    if not JOOBLE_API_KEY:
        return []
    
    url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
    
    # Mehrere Suchanfragen für bessere Abdeckung
    queries = [
        f"{zieljob} {branche}",
        f"{zieljob}",
    ]
    
    all_jobs = []
    seen_titles = set()
    
    async with httpx.AsyncClient(timeout=20.0) as http:
        for query in queries:
            try:
                resp = await http.post(url, json={
                    "keywords": query,
                    "location": "Deutschland",
                    "page": 1,
                })
                if resp.status_code == 200:
                    data = resp.json()
                    jobs = data.get("jobs", [])
                    for job in jobs:
                        title = job.get("title", "")
                        # Deduplizieren
                        if title.lower() not in seen_titles:
                            seen_titles.add(title.lower())
                            all_jobs.append({
                                "title": title,
                                "company": job.get("company", ""),
                                "location": job.get("location", ""),
                                "snippet": job.get("snippet", ""),
                                "salary": job.get("salary", ""),
                                "source": job.get("source", ""),
                                "type": job.get("type", ""),
                                "link": job.get("link", ""),
                                "updated": job.get("updated", ""),
                            })
                        if len(all_jobs) >= count:
                            break
            except Exception as e:
                print(f"Jooble API error for '{query}': {e}")
                continue
            
            if len(all_jobs) >= count:
                break
    
    return all_jobs


async def research_skills(zieljob: str, branche: str, aktueller_job: str) -> dict:
    """Recherchiert Skills aus echten Stellenanzeigen + generiert Kalibrierungs-Fragen."""

    # SCHRITT 1: Echte Stellen von Jooble holen
    jobs = await fetch_jooble_jobs(zieljob, branche, count=50)
    
    has_real_jobs = len(jobs) >= 5
    
    # SCHRITT 2: Claude analysiert
    if has_real_jobs:
        prompt = build_prompt_with_jobs(zieljob, branche, aktueller_job, jobs)
    else:
        prompt = build_prompt_fallback(zieljob, branche, aktueller_job, jobs)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    result = parse_json_response(response.content[0].text.strip())
    
    # Metadaten anreichern
    if "meta" not in result:
        result["meta"] = {}
    result["meta"]["stellenanzeigen_geladen"] = len(jobs)
    result["meta"]["quelle"] = "jooble" if has_real_jobs else "claude_fallback"
    
    return result


def build_prompt_with_jobs(zieljob, branche, aktueller_job, jobs):
    """Prompt mit ECHTEN Stellenanzeigen."""
    
    # Jobs als kompakten Text formatieren
    jobs_text = ""
    for i, job in enumerate(jobs[:40], 1):
        title = job.get("title", "?")
        company = job.get("company", "?")
        snippet = job.get("snippet", "")
        # HTML Tags aus Snippet entfernen
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()
        # Kürzen
        if len(snippet) > 400:
            snippet = snippet[:400] + "..."
        salary = job.get("salary", "")
        location = job.get("location", "")
        
        jobs_text += f"\n--- Stelle {i}: {title} bei {company} ({location}) ---\n"
        if salary:
            jobs_text += f"Gehalt: {salary}\n"
        jobs_text += f"{snippet}\n"
    
    return f"""Du bist ein Arbeitsmarkt-Analyst der ECHTE Stellenanzeigen auswertet.

Position: "{zieljob}" in "{branche}". User ist aktuell "{aktueller_job}".

## {len(jobs)} ECHTE Stellenanzeigen (gerade live von Jobbörsen geholt):

{jobs_text}

## Deine Aufgabe

### 1. Skills extrahieren (8-10 Skills)

Analysiere ALLE Stellenanzeigen und extrahiere die Skills die TATSÄCHLICH gefordert werden.
- Sortiere nach Häufigkeit: Was kommt in den MEISTEN Anzeigen vor?
- Unterscheide Hard Skills und Soft Skills
- Gewichtung = Wie oft der Skill vorkommt (0.0-1.0)
- Varianz = Wie UNTERSCHIEDLICH die Anforderungen sind

### 2. Kalibrierungs-Fragen (4-7 Fragen — EXTREM WICHTIG!)

Schau dir die Stellenanzeigen genau an. Du wirst sehen:
- Manche fordern Neukundenakquise, andere Bestandskundenpflege
- Manche wollen Führung von 5 Leuten, andere von 50
- Manche sind operativ, andere strategisch
- Manche fordern Branchenerfahrung, andere nicht

GENAU DIESE Unterschiede sind deine Kalibrierungs-Fragen!

Jede Frage muss sich aus einem ECHTEN Unterschied in den Anzeigen ergeben.
Zitiere im "grund"-Feld konkret: "In 12 von 30 Anzeigen steht X, in 18 steht Y"

REGELN:
- 4-7 Fragen — lieber eine zu viel als den Job falsch zu verstehen
- Jede Frage hat 2-3 inhaltliche Optionen PLUS eine Ausweichoption ("Beides", "Gemischt")
- Du-Form, einfache Sprache, keine HR-Fachbegriffe
- Jede Option verändert die Skill-Gewichtung MESSBAR

Antworte NUR mit JSON:
{get_json_template()}
"""


def build_prompt_fallback(zieljob, branche, aktueller_job, partial_jobs=None):
    """Fallback wenn zu wenige Stellen gefunden."""
    
    partial_text = ""
    if partial_jobs:
        for i, job in enumerate(partial_jobs[:10], 1):
            title = job.get("title", "?")
            snippet = re.sub(r'<[^>]+>', '', job.get("snippet", "")).strip()
            partial_text += f"\n{i}. {title}: {snippet[:200]}\n"
    
    return f"""Du bist ein Arbeitsmarkt-Experte.
Position: "{zieljob}" in "{branche}". User ist aktuell "{aktueller_job}".

{"Teilweise Daten gefunden:" + partial_text if partial_text else "Keine Live-Daten verfügbar."}

Nutze dein Wissen über ECHTE Stellenanzeigen für diese Position.

### 1. Skills (8-10)
Was fordern echte Stellenanzeigen für "{zieljob}" in "{branche}"?
Denke an konkrete Jobbörsen-Anzeigen die du kennst.

### 2. Kalibrierungs-Fragen (4-7 Fragen)

Die Position "{zieljob}" gibt es in VERSCHIEDENEN Ausprägungen.
Deine Fragen klären: WELCHE Ausprägung strebt der User an?

Beispiel-Dimensionen die du klären musst:
- Unternehmensgröße: Startup/KMU vs. Mittelstand vs. Konzern
- Führungsspanne: kleine vs. große Teams
- Fokus: operativ vs. strategisch
- Kundentyp: B2B vs. B2C vs. intern
- Reifegrad: Aufbau vs. Optimierung bestehender Strukturen

REGELN:
- 4-7 Fragen
- Du-Form, einfache Sprache
- 2-3 Optionen + Ausweichoption pro Frage
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
      "belege": ["Aus Anzeige X: Zitat", "In Y von Z Anzeigen gefordert"],
      "varianz": "hoch oder mittel oder niedrig",
      "varianz_erklaerung": "Warum unterscheiden sich die Anforderungen?"
    }
  ],
  "varianz_fragen": [
    {
      "frage": "Deine Rückfrage an den User (Du-Form)",
      "grund": "In X von Y Anzeigen steht A, in Z steht B — darum müssen wir fragen",
      "beeinflusst_skills": ["Skill 1", "Skill 2"],
      "optionen": [
        {"text": "Option A", "skill_anpassung": "Wie sich Skills ändern"},
        {"text": "Option B", "skill_anpassung": "Wie sich Skills ändern"},
        {"text": "Beides / Gemischt", "skill_anpassung": "Beide Bereiche relevant, breites Profil"}
      ]
    }
  ],
  "meta": {
    "quellen_analysiert": 30,
    "stellenanzeigen_gefunden": 30,
    "vertrauen": "hoch/mittel/niedrig",
    "vertrauen_grund": "30 echte Stellenanzeigen analysiert, klare Muster erkennbar"
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
