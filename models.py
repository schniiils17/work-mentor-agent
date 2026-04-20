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
    frage_nr: Optional[int] = None
    antwort: str  # "A", "B", "C", "D" oder Button-ID wie "start"
    reaction_time_ms: Optional[int] = None  # Wie lange der User gebraucht hat


class ContinueRequest(BaseModel):
    session_id: str  # Nach agent_message: "weiter bitte"


class SkillResearchRequest(BaseModel):
    zieljob: str
    branche: str
    aktueller_job: str


class SessionState(BaseModel):
    session_id: str
    zieljob: str
    aktueller_job: str
    branche: str
    skills: list[Skill]
    messages: list[dict]  # Claude conversation history
    fragen_gestellt: int = 0
    abgeschlossen: bool = False
