"""
Work Mentor Agent — Datenmodelle
"""

from pydantic import BaseModel
from typing import Optional


class Skill(BaseModel):
    name: str
    begruendung: str


class StartRequest(BaseModel):
    session_id: str
    zieljob: str
    aktueller_job: str
    branche: str
    skills: Optional[list[Skill]] = None  # Wenn leer, generiert der Agent sie selbst


class AnswerRequest(BaseModel):
    session_id: str
    frage_nr: int
    antwort: str  # "A", "B", "C", "D"
    reaction_time_ms: Optional[int] = None  # Wie lange der User gebraucht hat


class ContinueRequest(BaseModel):
    session_id: str  # Nach Magie-Moment: "weiter bitte"


class SessionState(BaseModel):
    session_id: str
    zieljob: str
    aktueller_job: str
    branche: str
    skills: list[Skill]
    messages: list[dict]  # Claude conversation history
    fragen_gestellt: int = 0
    abgeschlossen: bool = False
