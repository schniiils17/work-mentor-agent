"""
Work Mentor Agent — Kern-Logik
Spricht mit Claude API und verwaltet den Assessment-Flow.
"""

import json
import os
from anthropic import Anthropic
from system_prompt import build_system_prompt
from models import SessionState, Skill

# Claude Client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# In-Memory Session Storage (später: Redis oder DB)
sessions: dict[str, SessionState] = {}

# Default Skills wenn keine übergeben werden
DEFAULT_SKILLS_PROMPT = """
Basierend auf dem Zieljob, dem aktuellen Job und der Branche:
Definiere die 5 wichtigsten Skills die für den Zieljob relevant sind.
Antworte NUR mit einem JSON-Array:
[
  {"name": "Skill-Name", "begruendung": "Warum dieser Skill für den Job wichtig ist"}
]
Keine Erklärung, nur JSON.
"""


async def generate_skills(zieljob: str, aktueller_job: str, branche: str) -> list[Skill]:
    """Generiert 5 relevante Skills für den Zieljob via Claude."""
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"Zieljob: {zieljob}\nAktueller Job: {aktueller_job}\nBranche: {branche}\n\n{DEFAULT_SKILLS_PROMPT}"
            }
        ]
    )
    
    text = response.content[0].text.strip()
    # JSON aus der Antwort extrahieren
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    
    skills_data = json.loads(text)
    return [Skill(**s) for s in skills_data]


async def start_session(session_id: str, zieljob: str, aktueller_job: str, 
                         branche: str, skills: list[Skill] | None = None) -> dict:
    """Startet eine neue Assessment-Session."""
    
    # Skills generieren wenn nicht übergeben
    if not skills:
        skills = await generate_skills(zieljob, aktueller_job, branche)
    
    # System-Prompt bauen
    system_prompt = build_system_prompt(
        zieljob=zieljob,
        aktueller_job=aktueller_job,
        branche=branche,
        skills=[s.model_dump() for s in skills]
    )
    
    # Erste Nachricht an Claude: "Starte das Assessment"
    messages = [
        {
            "role": "user",
            "content": "Starte das Assessment. Schicke die erste Frage."
        }
    ]
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=system_prompt,
        messages=messages
    )
    
    assistant_text = response.content[0].text.strip()
    
    # Assistant-Antwort zur History hinzufügen
    messages.append({
        "role": "assistant",
        "content": assistant_text
    })
    
    # Session speichern
    session = SessionState(
        session_id=session_id,
        zieljob=zieljob,
        aktueller_job=aktueller_job,
        branche=branche,
        skills=skills,
        messages=messages,
        fragen_gestellt=1
    )
    sessions[session_id] = session
    
    # JSON aus der Antwort parsen
    return _parse_agent_response(assistant_text)


async def process_answer(session_id: str, frage_nr: int, antwort: str,
                          reaction_time_ms: int | None = None) -> dict:
    """Verarbeitet die Antwort des Users und gibt das nächste Element zurück."""
    
    session = sessions.get(session_id)
    if not session:
        return {"typ": "error", "code": "SESSION_NOT_FOUND", "message": "Session nicht gefunden."}
    
    if session.abgeschlossen:
        return {"typ": "error", "code": "ASSESSMENT_COMPLETE", "message": "Assessment ist bereits abgeschlossen."}
    
    # User-Antwort formulieren
    user_msg = f"Der User hat '{antwort}' gewählt."
    if reaction_time_ms is not None:
        user_msg += f" (Reaktionszeit: {reaction_time_ms}ms)"
    
    session.messages.append({
        "role": "user",
        "content": user_msg
    })
    
    # System-Prompt neu bauen (für Kontext)
    system_prompt = build_system_prompt(
        zieljob=session.zieljob,
        aktueller_job=session.aktueller_job,
        branche=session.branche,
        skills=[s.model_dump() for s in session.skills]
    )
    
    # Claude fragen
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=session.messages
    )
    
    assistant_text = response.content[0].text.strip()
    
    # Zur History hinzufügen
    session.messages.append({
        "role": "assistant",
        "content": assistant_text
    })
    
    # Fragen-Counter updaten
    parsed = _parse_agent_response(assistant_text)
    if parsed.get("typ") == "frage" or parsed.get("typ") == "praeferenz":
        session.fragen_gestellt += 1
    elif parsed.get("typ") == "abschluss":
        session.abgeschlossen = True
    
    return parsed


async def continue_after_magic(session_id: str) -> dict:
    """Fordert die nächste Frage nach einem Magie-Moment an."""
    
    session = sessions.get(session_id)
    if not session:
        return {"typ": "error", "code": "SESSION_NOT_FOUND", "message": "Session nicht gefunden."}
    
    session.messages.append({
        "role": "user",
        "content": "Weiter."
    })
    
    system_prompt = build_system_prompt(
        zieljob=session.zieljob,
        aktueller_job=session.aktueller_job,
        branche=session.branche,
        skills=[s.model_dump() for s in session.skills]
    )
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=system_prompt,
        messages=session.messages
    )
    
    assistant_text = response.content[0].text.strip()
    
    session.messages.append({
        "role": "assistant",
        "content": assistant_text
    })
    
    parsed = _parse_agent_response(assistant_text)
    if parsed.get("typ") == "frage" or parsed.get("typ") == "praeferenz":
        session.fragen_gestellt += 1
    
    return parsed


def _parse_agent_response(text: str) -> dict:
    """Parst die JSON-Antwort des Agents."""
    try:
        # Manchmal wrappen LLMs JSON in ```json ... ```
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: Versuche JSON aus dem Text zu extrahieren
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {
                "typ": "error",
                "code": "PARSE_ERROR",
                "message": "Agent-Antwort konnte nicht geparst werden.",
                "raw": text
            }
