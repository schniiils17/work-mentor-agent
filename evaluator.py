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
    
    prompt = f"""Du bist ein erfahrener Eignungsdiagnostiker.
Ein User hat ein Persönlichkeits-Assessment absolviert für den Zieljob "{zieljob}".

## GEMESSENE DIMENSIONEN (das sind die einzigen Daten die du hast!)
{scores_text}

## Einzelne Antworten
{answer_details}

## DEINE AUFGABE

Erstelle ein Ergebnis das die 7 GEMESSENEN Persönlichkeitsdimensionen im Kontext des Zieljobs "{zieljob}" interpretiert.

### WICHTIGE REGELN:

1. **NUR die 7 Dimensionen zeigen!** Du hast NUR Persönlichkeitsdaten. Erfinde KEINE Job-Skills wie "Key Account Management" oder "Budgetplanung". Du weißt nicht ob der User das kann — du weißt nur wie er TICKT.

2. **Jede Dimension durch die Job-Linse erklären.** Nicht "Deine Durchsetzung ist niedrig" (langweilig) sondern "Deine Durchsetzung ist niedrig — als {zieljob} heißt das: du wirst Meetings moderieren können, aber wenn einer nicht liefert wird dir das Kritikgespräch schwerfallen."

3. **Ehrlich aber motivierend.** Minimum Match-Score: 60%.
   - 60-69% = "Solide Basis mit Entwicklungsfeldern"
   - 70-79% = "Gut vorbereitet für diesen Schritt"  
   - 80-89% = "Sehr stark aufgestellt"
   - 90%+ = Nur bei perfektem Match

4. **Überraschende Verbindungen!** Der Mehrwert ist NICHT "du bist empathisch". Der Mehrwert ist: "Deine hohe Empathie + niedrige Durchsetzung = du wirst genau wissen dass dein Mitarbeiter Mist baut, aber nichts sagen. Das frisst dich auf."

5. **Sprache:** Du-Form, einfach, Berufsschulniveau. Kein HR-Jargon. NUR Deutsch.
   - NIEMALS "als wie" — immer NUR "als" ODER NUR "wie". Beispiel: "besser als andere" ✓, "besser wie andere" ✓ (umgangssprache), "besser als wie andere" ✗ VERBOTEN.
   - Schreibe "dass" mit Doppel-s.

6. **KEINE HALLUZINATIONEN!** Beziehe dich NUR auf die konkreten Antworten oben. Erfinde KEINE Details über den User (z.B. "dein Schreibtisch ist aufgeräumt", "du liest gerne"). Du weißt NICHTS über den User außer seinen Antworten. Wenn du ein Szenario beschreibst, mache klar dass es eine VORHERSAGE ist ("du wirst wahrscheinlich..."), nicht eine Beobachtung.

6. **Bewertung pro Dimension:** Überlege für JEDE Dimension: Wie wichtig ist sie für "{zieljob}"? Wie hoch SOLLTE sie sein? Wie hoch IST sie? Die Lücke bestimmt den Score.
8. **Bewertungs-Labels:** Verwende NUR diese 4 Labels: "Sehr stark", "Stark", "Ausgeglichen", "Entwicklungsbedarf". NICHT "Ausreichend" (klingt wie Schulnote 4), NICHT "Gut", NICHT "Lücke".

### DIMENSIONS-BEWERTUNG:
Für jede der 7 Dimensionen:
- Bestimme einen Zielwert (0-100) für den Job "{zieljob}"
- Vergleiche mit dem gemessenen Wert
- Berechne: dimension_score = max(60, 100 - abs(gemessen - zielwert))
- Der match_score ist der Durchschnitt aller dimension_scores

### OUTPUT FORMAT (JSON):

{{
  "match_score": 72,
  "match_label": "Kurzer Satz der das Ergebnis zusammenfasst",
  "dimensions": [
    {{
      "dimension": "durchsetzung",
      "label": "Durchsetzung",
      "user_score": 35,
      "job_relevanz": "hoch",
      "bewertung": "Entwicklungsbedarf",
      "insight": "Konkreter Insight im Job-Kontext. Was bedeutet dieser Score für DIESEN Job? 2-3 Sätze. Beziehe dich auf konkrete Antworten."
    }},
    {{
      "dimension": "empathie",
      "label": "Empathie",
      "user_score": 70,
      "job_relevanz": "hoch",
      "bewertung": "Stark",
      "insight": "..."
    }}
  ],
  "staerken": [
    {{
      "dimension": "...",
      "begruendung": "Überraschend formuliert — warum ist diese Dimension deine Superkraft für diesen Job?"
    }}
  ],
  "hauptgap": {{
    "dimension": "...",
    "label": "...",
    "beschreibung": "Was genau wird dir schwerfallen und WARUM — konkretes Szenario",
    "intensity": "low / medium / high"
  }},
  "bright_vs_dark": {{
    "beschreibung": "Welche zwei Dimensionen erzeugen einen überraschenden Kontrast? Was passiert wenn du unter Druck gerätst?"
  }},
  "motive": {{
    "profil": "2-4 Wörter die den User-Typ beschreiben",
    "job_fit": "Passt dieses Motiv-Profil zum {zieljob}? Warum/warum nicht?"
  }},
  "main_potential": "1 Satz: Dein größtes Pfund für diesen Job",
  "main_risk": "1 Satz: Dein größtes Risiko in diesem Job",
  "buchempfehlung": {{
    "titel": "Echtes deutsches oder übersetztes Buch das zum größten Hebel passt",
    "autor": "Echter Autor",
    "begruendung": "Warum genau dieses Buch für genau diesen User — beziehe dich auf den Hebel",
    "amazon_suchbegriff": "Suchbegriff für Amazon DE"
  }},
  "naechster_schritt": "1 konkreter, einfacher Tipp — kein generisches 'netzwerke mehr'"
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
