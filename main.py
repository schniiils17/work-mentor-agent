"""
Work Mentor Agent — API Server
FastAPI Backend für das adaptive Assessment.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import StartRequest, AnswerRequest, ContinueRequest
from agent import start_session, process_answer, continue_after_magic, sessions

# .env laden
load_dotenv()

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
            skills=req.skills
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
    if req.antwort not in ["A", "B", "C", "D"]:
        raise HTTPException(status_code=400, detail="Antwort muss A, B, C oder D sein.")
    
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
