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


async def clarify_job(zieljob: str, branche: str = "", aktueller_job: str = "") -> dict:
    """Runde 1: Zeigt die wahrscheinlichste Interpretation mit Kernaufgaben."""
    
    branche_text = f" in der Branche '{branche}'" if branche else ""
    aktueller_text = f" (aktuell: {aktueller_job})" if aktueller_job else ""
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": f"""Ein User hat als Zieljob eingegeben: "{zieljob}"{branche_text}{aktueller_text}

Deine Aufgabe:
1. Was ist die WAHRSCHEINLICHSTE Interpretation dieses Jobtitels?
2. Erstelle eine klare, kurze Beschreibung (2-3 Sätze, Du-Form, einfache Sprache)
3. Liste 4-6 KERNAUFGABEN auf die diesen Job ausmachen
4. Generiere 2-3 alternative Interpretationen für den Fall dass Runde 1 komplett falsch ist
5. Generiere 4-6 ZUSATZ-AUFGABEN die je nach Position dazugehören KÖNNTEN (für Feinjustierung)

WICHTIG bei der Interpretation:
- Denke vom KERN des Jobs: Was macht man den ganzen Tag?
- "Leiter digitaler Vertrieb" = Führungskraft die Verkäufer führt (die digital verkaufen), NICHT jemand der Marketing macht
- "Vertriebsleiter" = Führt und coached ein Verkaufsteam
- "Projektmanager" = Kann IT, Bau, Marketing etc. sein
- Unterscheide IMMER: Führt Menschen vs. Macht selbst vs. Managed Prozesse

Antworte NUR mit JSON:
{{
  "hauptinterpretation": {{
    "titel": "Kurzer Titel (3-5 Wörter)",
    "beschreibung": "2-3 Sätze was dieser Job bedeutet. Du-Form. Einfache Sprache. Fokus auf: Was machst du den ganzen Tag? Wen führst du? Was ist dein Ziel?",
    "kernaufgaben": ["Aufgabe 1", "Aufgabe 2", "Aufgabe 3", "Aufgabe 4"],
    "suchbegriffe": ["Suchbegriff für Jobbörse 1", "Suchbegriff 2"]
  }},
  "zusatz_aufgaben": [
    "Aufgabe die je nach Position dazugehören könnte",
    "Weitere optionale Aufgabe"
  ],
  "alternativen": [
    {{
      "titel": "Alternativer Titel",
      "beschreibung": "Was diese Alternative anders macht (1-2 Sätze, Du-Form)",
      "kernaufgaben": ["Andere Aufgabe 1", "Andere Aufgabe 2"],
      "suchbegriffe": ["Suchbegriff 1", "Suchbegriff 2"]
    }}
  ]
}}

Kernaufgaben = Was man SICHER in diesem Job macht (z.B. "Vertriebsteam führen und coachen")
Zusatz-Aufgaben = Was je nach Unternehmen DAZUKOMMEN könnte (z.B. "Eigene Kunden betreuen", "Budget verantworten")
Alternativen = Komplett ANDERE Jobs die der Titel auch meinen könnte

Gib IMMER 2-3 Alternativen und 4-6 Zusatz-Aufgaben."""}]
    )
    
    return parse_json_response(response.content[0].text.strip())


async def generate_search_queries(zieljob: str, branche: str) -> list[str]:
    """Lässt Claude smarte Suchbegriffe für Jobbörsen generieren."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": f"""Du bist ein Recruiter der auf Jobbörsen nach Stellen sucht.

Zieljob: "{zieljob}" in "{branche}"

Generiere 3-5 verschiedene Suchbegriffe die ein Recruiter auf Stepstone/Indeed eingeben würde um GENAU diese Position zu finden.

Wichtig:
- Verwende Synonyme und alternative Jobtitel
- Denke an das was der User WIRKLICH meint (z.B. "Leiter digitaler Vertrieb" = Vertriebsleiter der digitale Kanäle nutzt, NICHT Digital Marketing Manager)
- Jeder Suchbegriff max 3-4 Wörter
- Wenn eine Branche angegeben ist, nutze sie bei 1-2 Queries

Antworte NUR mit einem JSON-Array von Strings:
["Suchbegriff 1", "Suchbegriff 2", "Suchbegriff 3"]"""}]
    )
    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
            text = text.strip()
        queries = json.loads(text)
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            return queries[:5]
    except Exception:
        pass
    # Fallback
    return [f"{zieljob} {branche}", zieljob]


async def fetch_jooble_jobs(zieljob: str, branche: str, count: int = 50) -> list[dict]:
    """Holt echte Stellenanzeigen von Jooble API mit smarten Suchbegriffen."""
    if not JOOBLE_API_KEY:
        return []
    
    url = f"https://de.jooble.org/api/{JOOBLE_API_KEY}"
    
    # Claude generiert smarte Suchbegriffe
    queries = await generate_search_queries(zieljob, branche)
    
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


async def filter_relevant_jobs(jobs: list[dict], zieljob: str, branche: str) -> list[dict]:
    """Lässt Claude die wirklich relevanten Stellen auswählen."""
    if len(jobs) <= 5:
        return jobs
    
    # Kompakte Job-Liste für Claude
    job_list = ""
    for i, job in enumerate(jobs[:50]):
        title = job.get("title", "?")
        snippet = re.sub(r'<[^>]+>', '', job.get("snippet", "")).strip()[:150]
        job_list += f"{i}: {title} | {snippet}\n"
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": f"""Zieljob des Users: "{zieljob}" in "{branche}"

Hier sind Stellenanzeigen von Jobbörsen. Wähle NUR die Stellen aus die WIRKLICH zu diesem Zieljob passen.

Wichtig: 
- "Leiter digitaler Vertrieb" = Führungskraft die ein Vertriebsteam leitet (das digital verkauft), NICHT Digital Marketing Manager oder E-Commerce Manager
- "Vertriebsleiter" = Führt Verkäufer, NICHT Key Account Manager
- Achte auf den KERN des Jobs, nicht nur auf Keywords im Titel

Stellen:
{job_list}

Antworte NUR mit einem JSON-Array der Indizes der relevanten Stellen:
[0, 3, 7, 12]"""}]
    )
    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
            text = text.strip()
        indices = json.loads(text)
        if isinstance(indices, list):
            return [jobs[i] for i in indices if isinstance(i, int) and 0 <= i < len(jobs)]
    except Exception:
        pass
    return jobs[:20]  # Fallback: erste 20


async def research_skills(zieljob: str, branche: str, aktueller_job: str, job_beschreibung: str = "") -> dict:
    """Recherchiert Skills aus echten Stellenanzeigen + generiert Kalibrierungs-Fragen."""

    # SCHRITT 1: Echte Stellen von Jooble holen
    jobs = await fetch_jooble_jobs(zieljob, branche, count=50)
    
    # SCHRITT 1.5: Relevanz-Filter — nur Stellen die wirklich passen
    if len(jobs) >= 5:
        jobs = await filter_relevant_jobs(jobs, zieljob, branche)
    
    has_real_jobs = len(jobs) >= 3
    
    # SCHRITT 2: Claude analysiert
    if has_real_jobs:
        prompt = build_prompt_with_jobs(zieljob, branche, aktueller_job, jobs, job_beschreibung)
    else:
        prompt = build_prompt_fallback(zieljob, branche, aktueller_job, jobs, job_beschreibung)

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
    result["meta"]["stellenanzeigen_relevant"] = len(jobs)  # nach Filter
    result["meta"]["quelle"] = "jooble" if has_real_jobs else "claude_fallback"
    
    return result


def build_prompt_with_jobs(zieljob, branche, aktueller_job, jobs, job_beschreibung=""):
    """Prompt mit ECHTEN Stellenanzeigen."""
    
    klarifizierung = ""
    if job_beschreibung:
        klarifizierung = f"\n\n## WICHTIG: Der User hat klarifiziert was er meint:\n\"{job_beschreibung}\"\nAlle Skills und Fragen müssen sich auf DIESE Interpretation beziehen!\n"
    
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
{klarifizierung}
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
- Jede Option verändert die Skill-Gewichtung
- WICHTIG: Die Fragen beschreiben die POSITION, nicht die Präferenzen des Users!
  FALSCH: "Welche Sparte INTERESSIERT dich?" / "Was REIZT dich mehr?"
  RICHTIG: "Wie ist die Position ausgelegt?" / "Was würde dein Alltag sein?"
  Der User beschreibt den JOB, nicht seine Wünsche.
  Formuliere: "Wie würde dein Team aussehen?" statt "Welche Teamgröße strebst du an?" MESSBAR

Antworte NUR mit JSON:
{get_json_template()}
"""


def build_prompt_fallback(zieljob, branche, aktueller_job, partial_jobs=None, job_beschreibung=""):
    """Fallback wenn zu wenige Stellen gefunden."""
    
    klarifizierung = ""
    if job_beschreibung:
        klarifizierung = f"\nWICHTIG: Der User hat klarifiziert was er meint: \"{job_beschreibung}\"\n"
    
    partial_text = ""
    if partial_jobs:
        for i, job in enumerate(partial_jobs[:10], 1):
            title = job.get("title", "?")
            snippet = re.sub(r'<[^>]+>', '', job.get("snippet", "")).strip()
            partial_text += f"\n{i}. {title}: {snippet[:200]}\n"
    
    return f"""Du bist ein Arbeitsmarkt-Experte.
Position: "{zieljob}" in "{branche}". User ist aktuell "{aktueller_job}".
{klarifizierung}
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
- WICHTIG: Die Fragen beschreiben die POSITION, nicht die Präferenzen des Users!
  FALSCH: "Welche Sparte INTERESSIERT dich?" / "Was REIZT dich mehr?"
  RICHTIG: "Wie ist die Position ausgelegt?" / "Was würde dein Alltag sein?"
  Der User beschreibt den JOB, nicht seine Wünsche.
  Formuliere: "Wie würde dein Team aussehen?" statt "Welche Teamgröße strebst du an?"

Antworte NUR mit JSON:
{get_json_template()}
"""


async def research_diagnostik_strategy(zieljob: str, branche: str, skills: list[dict], job_beschreibung: str = "") -> dict:
    """Recherchiert die beste diagnostische Strategie pro Skill.
    
    Fragt: Wie testet man diese Skills laut Forschung am besten?
    Welche Persönlichkeitsmerkmale unterscheiden gute von schlechten Kandidaten?
    Welche Szenario-Typen liefern die besten Datenpunkte?
    """
    
    skills_text = ""
    for i, skill in enumerate(skills[:7], 1):
        name = skill.get("name", "?")
        kat = skill.get("kategorie", "?")
        skills_text += f"\n{i}. {name} ({kat})"
    
    beschreibung_text = ""
    if job_beschreibung:
        beschreibung_text = f"\nKlarifizierung: {job_beschreibung}"
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": f"""Du bist ein Experte für Eignungsdiagnostik und psychologische Testverfahren.

Zieljob: "{zieljob}" in "{branche}"{beschreibung_text}

Diese Skills wurden als relevant identifiziert:{skills_text}

Deine Aufgabe — recherchiere für JEDEN Skill:

### 1. Persönlichkeitsforschung
Was sagt die Forschung (Hogan, Big Five, DISC, BIP etc.) darüber, welche Persönlichkeitsmerkmale bei DIESEM Skill den Unterschied zwischen gut und schlecht machen?
- Welche Traits korrelieren mit Erfolg in diesem Skill?
- Welche Dark-Side-Traits führen zum Scheitern?
- Gibt es bekannte Studien oder Benchmarks?

### 2. Diagnostische Strategie
Wie misst man diesen Skill am besten OHNE dass der Kandidat es merkt?
- Welche Methode eignet sich? (Statement, Forced Choice, Szenario, Ranking)
- Welche ALLTAGS-Situation wäre ein guter Proxy?
- Was ist der häufigste Fehler bei der Messung dieses Skills?

### 3. Differenzierungs-Dimensionen
Welche 2-4 Verhaltensstrategien gibt es bei diesem Skill?
Beispiel für "Führungskompetenz":
- Strategie A: Autoritär/Entscheidungsfreudig
- Strategie B: Demokratisch/Konsensorientiert  
- Strategie C: Coaching/Entwicklungsorientiert
- Strategie D: Laissez-faire/Delegierend
→ KEINE ist "besser", aber jede passt zu einem anderen Kontext.

### 4. Anti-Durchschaubarkeit
Wie formuliert man Fragen so, dass der Kandidat NICHT erraten kann was gemessen wird?
Welche Fallen vermeiden gute Diagnostiker?

Antworte NUR mit JSON:
{{
  "skills_diagnostik": [
    {{
      "skill": "Skill-Name",
      "persoenlichkeit": {{
        "erfolgs_traits": ["Trait 1", "Trait 2"],
        "dark_side_traits": ["Trait 1", "Trait 2"],
        "forschung": "Was sagt die Forschung (1-2 Sätze)"
      }},
      "diagnostik_strategie": {{
        "beste_methode": "statement / forced_choice / szenario",
        "alltags_proxy": "Welche Alltagssituation misst das am besten",
        "haeufigster_fehler": "Was man vermeiden muss"
      }},
      "dimensionen": [
        {{
          "name": "Strategie A",
          "beschreibung": "Was diese Strategie bedeutet",
          "wann_gut": "In welchem Kontext das die beste Strategie ist"
        }}
      ],
      "anti_durchschaubarkeit": "Tipp wie man es unsichtbar misst"
    }}
  ],
  "allgemeine_tipps": [
    "Übergreifende Empfehlungen für diesen Zieljob"
  ],
  "meta": {{
    "quellen": ["Hogan", "Big Five", etc.],
    "vertrauen": "hoch/mittel/niedrig"
  }}
}}"""}]
    )
    
    return parse_json_response(response.content[0].text.strip())


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
      "frage": "Frage über die POSITION, nicht über Präferenzen (Du-Form). Z.B. 'Wie groß wäre dein Team in dieser Position?'",
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
