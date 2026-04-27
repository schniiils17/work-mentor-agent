"""
Work Mentor — Evaluator v2
Zeigt die 7 GEMESSENEN Dimensionen im Kontext des Zieljobs.
Keine Fake-Skills — nur was wir tatsächlich gemessen haben.
"""

import json
import os
from anthropic import Anthropic
from statement_pool import DIMENSIONS

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def evaluate_assessment(
    zieljob: str,
    aktueller_job: str,
    branche: str,
    job_beschreibung: str,
    researched_skills: list[dict],
    varianz_antworten: list[dict],
    diagnostik_strategy: dict | None,
    dimension_scores: dict,
    answers: list[dict],
    job_fokus: str = "",
) -> dict:
    """Claude interpretiert die 7 Dimension-Scores im Job-Kontext → Dashboard."""
    
    # Scores als lesbaren Text mit allen Details
    scores_text = ""
    for dim_key, score in dimension_scores.items():
        dim = DIMENSIONS.get(dim_key, {})
        label = dim.get("label", dim_key)
        hoch = dim.get("hoch_heisst", "")
        niedrig = dim.get("niedrig_heisst", "")
        pole = dim.get("pole", ["", ""])
        
        pct = round(score * 100)
        if score >= 0.7:
            beschr = f"HOCH ({pct}%) — {hoch}"
        elif score <= 0.3:
            beschr = f"NIEDRIG ({pct}%) — {niedrig}"
        else:
            beschr = f"MITTEL ({pct}%) — Balance zwischen {pole[0]} und {pole[1]}"
        
        scores_text += f"\n- **{label}** ({dim_key}): {beschr}"
    
    # Antwort-Details für spezifische Insights
    answer_details = ""
    for ans in answers[:20]:
        antwort = ans.get("antwort", "?")
        text = ans.get("item_text", "")
        if text:
            antwort_text = "Stimmt" if antwort == "A" else "Stimmt nicht" if antwort == "B" else antwort
            answer_details += f"\n- \"{text}\" → {antwort_text}"
    
    # Job-Fokus in lesbaren Text
    fokus_map = {
        "team": "Schwerpunkt: Team führen, Strategie, interne Meetings (NICHT viel direkter Kundenkontakt)",
        "kunden": "Schwerpunkt: Selbst Kunden betreuen, Termine, Verhandlungen",
        "mix": "Mix aus Team-Führung und direktem Kundenkontakt",
    }
    fokus_text = fokus_map.get(job_fokus, "")
    fokus_section = f"\n\n## JOB-FOKUS DES USERS\n{fokus_text}\nBERUCKSICHTIGE DAS! Wenn der User sagt er führt ein Team, rede nicht von Kaltakquise oder Kundenterminen." if fokus_text else ""

    prompt = f"""Du bist ein erfahrener Eignungsdiagnostiker.
Ein User hat ein KURZES Persönlichkeits-Assessment (21 Fragen) absolviert für den Zieljob "{zieljob}".{fokus_section}

## GEMESSENE DIMENSIONEN
{scores_text}

## Einzelne Antworten
{answer_details}

## DEINE AUFGABE

Erstelle ein Ergebnis das die 7 Dimensionen als TENDENZEN im Kontext des Zieljobs "{zieljob}" zeigt.

### TONALITÄT — DAS WICHTIGSTE:

1. **TENDENZEN, keine Diagnosen.** Du hast 21 Fragen — das reicht für Richtungen, nicht für Urteile.
   - ✅ "Du neigst dazu, erstmal zuzuhören bevor du dich einbringst"
   - ✅ "Struktur und Planung scheinen dir zu liegen"
   - ✅ "Du bist tendenziell eher der Typ, der..."
   - ❌ "Du vergisst keine Termine" (zu absolut)
   - ❌ "Kaltakquise wird dir nicht liegen" (Urteil über Fähigkeit die wir nicht getestet haben)
   - ❌ "Du wirst das schwierige Gespräch zu lange aufschieben" (Vorhersage als Fakt)

2. **Respektvoll, nie belehrend.** Der User soll sich verstanden fühlen, nicht bewertet.
   - ✅ "Konfrontation kostet dich tendenziell mehr Energie — das ist weder gut noch schlecht"
   - ❌ "Du wirst zu lange höflich bleiben" (wertend)
   - ❌ "Das wird ein Problem" (bedrohlich)
   Statt "wird" → "könnte", "kann", "tendenziell".

3. **Keine Job-Vorhersagen die über die Dimension hinausgehen.**
   - ✅ "Durchsetzung ist bei Führungsrollen wichtig — hier gibt es Potenzial nach oben"
   - ❌ "Budgetverhandlungen werden zäh" (wissen wir nicht)
   - ❌ "Kaltakquise wird dir nicht liegen" (leitet zu viel ab)
   Bleib bei dem was die Dimension aussagt. Keine konkreten Job-Szenarien erfinden.

4. **Kurze Insights.** 1-2 Sätze pro Dimension. Nicht 3-4. Dicht und konkret.

5. **NUR die 7 Dimensionen.** Keine Job-Skills erfinden.

6. **Sprache:** Du-Form, einfach, Berufsschulniveau. NUR Deutsch.
   - NIEMALS "als wie" — nur "als" ODER "wie".

7. **Keine Halluzinationen.** Erfinde NICHTS über den User. Kein "dein Schreibtisch", kein "du liest gerne". Nur was aus den Antworten folgt.

8. **Bewertungs-Labels:** NUR diese 4: "Sehr stark", "Stark", "Ausgeglichen", "Entwicklungsbedarf".

9. **Match-Score:** Minimum 60%.
   - 60-69% = Solide Basis
   - 70-79% = Gut vorbereitet
   - 80-89% = Sehr stark aufgestellt
   - 90%+ = Nur bei perfektem Match

### OUTPUT FORMAT (JSON):

{{
  "match_score": 72,
  "match_label": "Kurzer ermutigender Satz — keine Kritik im Header",
  "dimensions": [
    {{
      "dimension": "durchsetzung",
      "label": "Durchsetzung",
      "user_score": 35,
      "job_relevanz": "hoch",
      "bewertung": "Entwicklungsbedarf",
      "insight": "1-2 Sätze als TENDENZ formuliert. Was bedeutet diese Richtung für den Job?"
    }}
  ],
  "staerken": [
    {{
      "dimension": "...",
      "begruendung": "Warum ist diese Tendenz ein Vorteil für den Job? Kurz und überraschend."
    }}
  ],
  "hauptgap": {{
    "dimension": "...",
    "label": "...",
    "beschreibung": "Was KÖNNTE herausfordernd werden — als Möglichkeit formuliert, nicht als Urteil",
    "intensity": "low / medium / high"
  }},
  "bright_vs_dark": {{
    "beschreibung": "Welche zwei Dimensionen erzeugen einen interessanten Kontrast? Was KÖNNTE unter Druck passieren?"
  }},
  "motive": {{
    "profil": "2-4 Wörter Typ-Beschreibung",
    "job_fit": "Kurzer Satz ob der Typ zum Job passt"
  }},
  "main_potential": "1 Satz: Dein größtes Pfund",
  "main_risk": "1 Satz: Worauf du achten solltest — als freundlicher Hinweis",
  "buchempfehlung": {{
    "titel": "Echtes deutsches/übersetztes Buch",
    "autor": "Echter Autor",
    "begruendung": "Warum dieses Buch für diesen User — kurz",
    "amazon_suchbegriff": "Suchbegriff für Amazon DE"
  }},
  "naechster_schritt": "1 konkreter einfacher Tipp"
}}

Antworte NUR mit dem JSON-Objekt. Kein Fließtext, keine Erklärung."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = response.content[0].text.strip()
    
    # JSON parsen
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
            return {"error": "parse_failed", "raw": text[:500]}
