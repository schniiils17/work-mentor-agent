"""
Work Mentor Agent — Datenmodelle
"""

from pydantic import BaseModel
from typing import Optional


class Skill(BaseModel):
    name: str
    begruendung: str
    kategorie: Optional[str] = None  # hard_skill / soft_skill
    gewichtung: Optional[float] = None  # 0.0 - 1.0
    varianz: Optional[str] = None  # hoch / mittel / niedrig


class ResearchedSkill(BaseModel):
    """Skill aus der Skill-Research-Engine (reichere Daten)."""
    name: str
    kategorie: str  # hard_skill / soft_skill
    gewichtung: float  # 0.0 - 1.0
    belege: list[str] = []
    varianz: str = "niedrig"  # hoch / mittel / niedrig
    varianz_erklaerung: str = ""


class VarianzAntwort(BaseModel):
    """Antwort auf eine Varianz-Rückfrage."""
    frage: str
    antwort: str  # Die gewählte Option
    skill_anpassung: str  # Wie sich die Skills ändern


class StartRequest(BaseModel):
    session_id: str
    zieljob: str
    aktueller_job: str
    branche: str
    skills: Optional[list[Skill]] = None  # Legacy: einfache Skills
    researched_skills: Optional[list[ResearchedSkill]] = None  # NEU: aus Skill-Research
    varianz_antworten: Optional[list[VarianzAntwort]] = None  # NEU: Antworten auf Rückfragen


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
