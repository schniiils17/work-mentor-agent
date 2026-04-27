"""
Work Mentor Agent — API Server
FastAPI Backend für das adaptive Assessment.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import StartRequest, AnswerRequest, ContinueRequest, SkillResearchRequest, JobClarifyRequest, DiagnostikStrategyRequest, ItemsRequest, EvaluateRequest
from agent import start_session, process_answer, continue_after_magic, sessions
from skill_research import research_skills, clarify_job, research_diagnostik_strategy
from statement_pool import select_items_for_session, score_answers
from evaluator import evaluate_assessment
from anthropic import Anthropic

# .env laden
load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# App erstellen
app = FastAPI(
    title="Work Mentor Agent",
    description="Adaptiver Eignungsdiagnostik-Agent für Job-Readiness-Checks",
    version="2.0.0"
)

# CORS erlauben (damit dein Frontend zugreifen kann)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Später einschränken auf deine Domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health Check"""
    return {
        "status": "online",
        "service": "Work Mentor Agent",
        "version": "2.0.0"
    }


@app.get("/api/health")
async def health():
    """Health Check für Monitoring"""
    return {"status": "healthy", "active_sessions": len(sessions)}


@app.post("/api/jobs/clarify")
async def api_job_clarify(req: JobClarifyRequest):
    """
    Prüft ob ein Zieljob eindeutig ist und bietet Interpretationen an.
    
    Schickt: zieljob, branche (optional), aktueller_job (optional)
    Bekommt: eindeutig (bool) + Interpretationen
    """
    try:
        result = await clarify_job(
            zieljob=req.zieljob,
            branche=req.branche,
            aktueller_job=req.aktueller_job
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/context")
async def api_job_context(req: JobClarifyRequest):
    """
    Smarter Kontext-Check: Claude entscheidet ob eine Rückfrage nötig ist.
    Wenn ja: generiert 1 Klick-Frage mit 2-3 passenden Optionen.
    Wenn nein: gibt needs_clarification=false zurück.
    """
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": f"""Ein User will einen Job-Readiness-Check machen für: "{req.zieljob}"

Entscheide: Ist der Job EINDEUTIG genug um die Persönlichkeits-Auswertung zu kontextualisieren?

Eindeutig = Wir wissen grob was der Alltag aussieht.
- "Softwareentwickler" → eindeutig (schreibt Code, Löst Probleme)
- "Lehrer" → eindeutig (unterrichtet, betreut Schüler)
- "Krankenpfleger" → eindeutig

Mehrdeutig = Gleicher Titel, aber völlig anderer Alltag möglich.
- "Vertriebsleiter" → mehrdeutig (Führt Team ODER ist selbst draußen?)
- "Berater" → mehrdeutig (Intern oder beim Kunden?)
- "Projektmanager" → mehrdeutig (IT, Bau, Marketing?)

Wenn MEHRDEUTIG: Generiere genau 1 Frage mit 2-3 Klick-Optionen.
Die Frage soll den GRÖSSTEN Unterschied im Alltag klären.
Optionen: Kurz, klar, mit Emoji. Alltagssprache.

Antworte NUR mit JSON:
{{
  "needs_clarification": true/false,
  "frage": "Wie sieht dein Alltag als [Job] eher aus?" (nur wenn needs_clarification=true),
  "optionen": [
    {{"id": "a", "text": "🏢 Kurze Beschreibung Option A"}},
    {{"id": "b", "text": "🤝 Kurze Beschreibung Option B"}}
  ] (nur wenn needs_clarification=true),
  "kontext_wenn_klar": "1 Satz was der Job bedeutet" (nur wenn needs_clarification=false)
}}"""}]
        )
        
        import json
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except Exception as e:
        # Bei Fehler: einfach keine Frage stellen
        return {"needs_clarification": False, "kontext_wenn_klar": req.zieljob}


@app.post("/api/skills/diagnostik")
async def api_diagnostik_strategy(req: DiagnostikStrategyRequest):
    """
    Recherchiert die beste diagnostische Strategie pro Skill.
    
    Schickt: zieljob, branche, skills (aus Research), job_beschreibung
    Bekommt: Pro Skill: Persönlichkeitsforschung, Teststrategie, Dimensionen
    """
    try:
        result = await research_diagnostik_strategy(
            zieljob=req.zieljob,
            branche=req.branche,
            skills=req.skills,
            job_beschreibung=req.job_beschreibung
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/research")
async def api_skill_research(req: SkillResearchRequest):
    """
    Recherchiert echte Skills aus Stellenanzeigen + Web-Quellen.
    
    Schickt: zieljob, branche, aktueller_job
    Bekommt: Skills mit Gewichtung + Rückfragen
    """
    try:
        result = await research_skills(
            zieljob=req.zieljob,
            branche=req.branche,
            aktueller_job=req.aktueller_job,
            job_beschreibung=req.job_beschreibung
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assessment/items")
async def api_items(req: ItemsRequest):
    """
    Gibt die Statement-Items für diese Session zurück.
    Frontend rendert sie — keine KI-Generierung nötig.
    
    Schickt: session_id
    Bekommt: Liste von 21 Items (14 Statements + 7 Forced Choice)
    """
    items = select_items_for_session(n_statements=14, n_forced=7)
    
    # In Frontend-Format umwandeln
    formatted = []
    for i, item in enumerate(items, 1):
        total = len(items)
        
        if item["typ"] == "statement":
            formatted.append({
                "typ": "statement",
                "item_id": item["id"],
                "statement_nr": i,
                "text": item["text"],
                "optionen": [
                    {"id": "A", "text": "\u2713 Stimmt"},
                    {"id": "B", "text": "\u2717 Stimmt nicht"}
                ],
                "progress": {"current": i, "estimated_total": total, "phase": "statements"}
            })
        elif item["typ"] == "forced_choice":
            formatted.append({
                "typ": "forced_choice",
                "item_id": item["id"],
                "statement_nr": i,
                "frage": item["frage"],
                "optionen": [
                    {"id": "A", "text": item["option_a"]},
                    {"id": "B", "text": item["option_b"]}
                ],
                "progress": {"current": i, "estimated_total": total, "phase": "statements"}
            })
    
    return {"items": formatted, "total": len(formatted)}


@app.post("/api/assessment/evaluate")
async def api_evaluate(req: EvaluateRequest):
    """
    Wertet das Assessment aus.
    Frontend schickt alle Antworten + Scores.
    Claude interpretiert im Job-Kontext → Dashboard.
    
    Schickt: dimension_scores, answers, job-kontext
    Bekommt: Dashboard
    """
    try:
        # Scores nochmal berechnen (Server-seitig verifizieren)
        verified_scores = score_answers(req.answers)
        
        dashboard = await evaluate_assessment(
            zieljob=req.zieljob,
            aktueller_job=req.aktueller_job,
            branche=req.branche,
            job_beschreibung=req.job_beschreibung,
            researched_skills=[s.model_dump() for s in req.researched_skills] if req.researched_skills else [],
            varianz_antworten=[va.model_dump() for va in req.varianz_antworten] if req.varianz_antworten else [],
            diagnostik_strategy=req.diagnostik_strategy,
            dimension_scores=verified_scores,
            answers=req.answers,
            job_fokus=req.job_fokus,
        )
        
        return {
            "typ": "abschluss",
            "messages": [
                {"text": "Danke — ich hab alles was ich brauche.", "delay_ms": 1500},
                {"text": "Hier ist dein Ergebnis.", "delay_ms": 1000}
            ],
            "dashboard": dashboard,
            "dimension_scores": verified_scores
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assessment/start")
async def api_start(req: StartRequest):
    """
    Startet ein neues Assessment.
    
    Schickt: session_id, zieljob, aktueller_job, branche
    Bekommt: Erste Frage
    """
    try:
        result = await start_session(
            session_id=req.session_id,
            zieljob=req.zieljob,
            aktueller_job=req.aktueller_job,
            branche=req.branche,
            skills=req.skills,
            researched_skills=req.researched_skills,
            varianz_antworten=req.varianz_antworten,
            diagnostik_strategy=req.diagnostik_strategy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assessment/answer")
async def api_answer(req: AnswerRequest):
    """
    Verarbeitet eine User-Antwort.
    
    Schickt: session_id, frage_nr, antwort (A/B/C/D)
    Bekommt: Nächste Frage / Magie-Moment / Dashboard
    """
    valid_answers = ["A", "B", "C", "D", "start", "ja", "nein", "weiter", "stimmt", "stimmt nicht"]
    if req.antwort.upper() not in [a.upper() for a in valid_answers] and req.antwort.upper() not in ["A", "B", "C", "D"]:
        raise HTTPException(status_code=400, detail="Ungültige Antwort.")
    
    try:
        result = await process_answer(
            session_id=req.session_id,
            frage_nr=req.frage_nr,
            antwort=req.antwort,
            reaction_time_ms=req.reaction_time_ms
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assessment/continue")
async def api_continue(req: ContinueRequest):
    """
    Fordert die nächste Frage nach einem Magie-Moment an.
    
    Schickt: session_id
    Bekommt: Nächste Frage
    """
    try:
        result = await continue_after_magic(req.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Debug: Session-Status abrufen."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")
    
    return {
        "session_id": session.session_id,
        "zieljob": session.zieljob,
        "aktueller_job": session.aktueller_job,
        "branche": session.branche,
        "skills": [s.model_dump() for s in session.skills],
        "fragen_gestellt": session.fragen_gestellt,
        "abgeschlossen": session.abgeschlossen
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
