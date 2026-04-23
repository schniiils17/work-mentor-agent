"""
Work Mentor — Evaluator
Claude interpretiert Persönlichkeits-Scores im Kontext des Zieljobs.
Keine Fragen-Generierung — nur Interpretation.
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
    """Claude interpretiert die Dimension-Scores im Job-Kontext → Dashboard."""
    
    # Scores als lesbaren Text
    scores_text = ""
    for dim_key, score in dimension_scores.items():
        dim = DIMENSIONS.get(dim_key, {})
        label = dim.get("label", dim_key)
        hoch = dim.get("hoch_heisst", "")
        niedrig = dim.get("niedrig_heisst", "")
        
        if score >= 0.7:
            beschr = f"HOCH ({score}) — {hoch}"
        elif score <= 0.3:
            beschr = f"NIEDRIG ({score}) — {niedrig}"
        else:
            beschr = f"MITTEL ({score}) — Balance zwischen beiden Polen"
        
        scores_text += f"\n- **{label}**: {beschr}"
    
    # Skills als Text
    skills_text = ""
    if researched_skills:
        sorted_skills = sorted(researched_skills, key=lambda s: s.get('gewichtung', 0), reverse=True)
        for i, skill in enumerate(sorted_skills[:7], 1):
            name = skill.get('name', '?')
            gew = skill.get('gewichtung', 0)
            skills_text += f"\n{i}. {name} (Gewichtung: {gew})"
    
    # Varianz-Kontext
    varianz_text = ""
    if varianz_antworten:
        for va in varianz_antworten:
            varianz_text += f"\n- {va.get('frage', '?')} → {va.get('antwort', '?')}"
    
    # Diagnostik-Kontext (wenn vorhanden)
    diagnostik_text = ""
    if diagnostik_strategy:
        skills_diag = diagnostik_strategy.get("skills_diagnostik", [])
        for sd in skills_diag[:5]:
            skill = sd.get("skill", "?")
            pers = sd.get("persoenlichkeit", {})
            erfolg = pers.get("erfolgs_traits", [])
            dark = pers.get("dark_side_traits", [])
            if erfolg or dark:
                diagnostik_text += f"\n- {skill}: Erfolg={', '.join(erfolg[:3])}. Risiko={', '.join(dark[:3])}"
    
    # Job-Beschreibung
    job_text = f"\nKlarifizierung: {job_beschreibung}" if job_beschreibung else ""
    
    # Antwort-Details für spezifische Insights
    answer_details = ""
    for ans in answers[:20]:
        item_id = ans.get("item_id", "?")
        antwort = ans.get("antwort", "?")
        text = ans.get("item_text", "")
        if text:
            antwort_text = "Stimmt" if antwort == "A" else "Stimmt nicht" if antwort == "B" else antwort
            answer_details += f"\n- \"{text}\" → {antwort_text}"
    
    prompt = f"""Du bist ein erfahrener Eignungsdiagnostiker.
Ein User hat ein Persönlichkeits-Assessment absolviert.

## Zieljob (DAS bewerten wir!)
**{zieljob}** in **{branche}**

## Aktueller Job (nur als Hintergrund-Info, NICHT im Dashboard erwähnen!)
{aktueller_job}
{job_text}

WICHTIG: Das Dashboard bewertet AUSSCHLIESSLICH die Eignung für den ZIELJOB "{zieljob}".
Der aktuelle Job "{aktueller_job}" ist NUR Kontext — erwähne ihn NICHT in den Insights.
Schreibe NICHT "Deine Trainer-Erfahrung" oder "Als {aktueller_job} bringst du...".
Der User will wissen ob er für den NEUEN Job passt, nicht was er jetzt schon kann.

## Kalibrierung
{varianz_text if varianz_text else "Keine Kalibrierungsdaten"}

## Recherchierte Skills (aus echten Stellenanzeigen)
{skills_text if skills_text else "Keine Skills recherchiert"}

## Forschungs-Kontext
{diagnostik_text if diagnostik_text else "Keine Diagnostik-Strategie"}

## PERSÖNLICHKEITSPROFIL DES USERS

{scores_text}

## Einzelne Antworten (für spezifische Insights)
{answer_details}

## DEINE AUFGABE

Erstelle ein Dashboard das die Persönlichkeit des Users mit den Anforderungen des Zieljobs verbindet.

### REGELN:
1. **Spezifisch!** Kein Barnum-Effekt. Beziehe dich auf KONKRETE Scores und Antworten.
2. **Ehrlich aber motivierend!** Minimum-Score ist 60%. Niemand unter 60%.
   - 60-69% = "Solide Basis mit Entwicklungsfeldern"
   - 70-79% = "Gut vorbereitet für diesen Schritt"
   - 80-89% = "Sehr stark aufgestellt"
   - 90%+ = Nur bei wirklich perfektem Match
3. **Überraschend!** Der Mehrwert ist NICHT "du bist empathisch" (das weiß der User). 
   Der Mehrwert ist die VERBINDUNG: "Dein Profil + dieser Job = DIESES konkrete Problem das du noch nicht siehst."
4. **Sprache:** Du-Form, einfach, Berufsschulniveau. Kein HR-Jargon. NUR Deutsch.
   NIEMALS "als wie" schreiben — das ist grammatikalisch falsch. Immer "als" ODER "wie", nie zusammen.
5. **Dimension-zu-Skill Mapping:** Erkläre WARUM ein bestimmter Dimension-Score für einen bestimmten Skill relevant ist.
6. **Skill-Namen klar halten:** Keine Abkürzungen oder Fachbegriffe. "CRM" → "Kundenbeziehungen aufbauen". "KPI" → "Ziele setzen und nachverfolgen". Der User muss sofort verstehen was gemeint ist.

### MAPPING-LOGIK:
Für jeden Skill überlege:
- Welche Dimensionen sind für diesen Skill am wichtigsten?
- Wie hoch müssten sie sein?
- Wie hoch SIND sie beim User?
- Was ist die Lücke?

Beispiel:
Skill "Teamführung" braucht: Durchsetzung HOCH + Empathie HOCH
User hat: Durchsetzung NIEDRIG + Empathie HOCH
→ "Du bist empathisch und spürst was dein Team braucht — aber dir fehlt die Bereitschaft unpopuläre Entscheidungen zu treffen."

### OUTPUT FORMAT (JSON):

{{
  "match_score": 72,
  "match_label": "Du bist auf einem guten Weg",
  "dimensions": [
    {{
      "skill": "Skill-Name aus der Recherche",
      "score": 75,
      "bewertung": "Stark / Solide / Entwicklungsbedarf / Lücke",
      "insight": "Spezifischer Insight der Score UND konkrete Antwort verbindet. 1-2 Sätze."
    }}
  ],
  "staerken": [
    {{"skill": "...", "begruendung": "Überraschend formuliert, bezieht sich auf Scores"}}
  ],
  "hauptgap": {{
    "skill": "...",
    "hauptluecke": "Was genau fehlt und warum",
    "gap_intensity": "low / medium / high"
  }},
  "bright_vs_dark": {{
    "unterschied": true,
    "beschreibung": "Welche Dimension zeigt einen überraschenden Kontrast?"
  }},
  "motive": {{
    "profil": "2-3 Wörter die den User beschreiben",
    "job_fit": "Wie passt das Motivationsprofil zum Zieljob?"
  }},
  "main_potential": "1 Satz: Größtes Pfund des Users für diesen Job",
  "main_risk": "1 Satz: Größtes Risiko des Users für diesen Job",
  "buchempfehlung": {{
    "titel": "Echtes Buch das zum größten Hebel passt",
    "autor": "Echter Autor",
    "begruendung": "Warum genau dieses Buch für genau diesen User",
    "amazon_suchbegriff": "Suchbegriff für Amazon"
  }},
  "naechster_schritt": "1 konkreter Tipp was der User JETZT tun kann"
}}

Antworte NUR mit JSON. Kein Fließtext."""

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
