# Work Mentor Agent 2.0

Adaptiver Eignungsdiagnostik-Agent für Job-Readiness-Checks.

## Setup

### 1. Environment Variables
Kopiere `.env.example` zu `.env` und trage deinen Anthropic API Key ein:
```
ANTHROPIC_API_KEY=sk-ant-dein-key-hier
```

### 2. Lokal testen
```bash
pip install -r requirements.txt
python main.py
```
Server läuft auf `http://localhost:8000`

### 3. Deploy auf Railway
1. Push diesen Code zu GitHub
2. Geh auf railway.app → New Project → Deploy from GitHub
3. Wähle dieses Repo
4. Füge unter Variables `ANTHROPIC_API_KEY` hinzu
5. Fertig — Railway gibt dir eine URL

## API Endpunkte

### POST /api/assessment/start
Startet ein Assessment.
```json
{
  "session_id": "uuid",
  "zieljob": "Vertriebsleiter",
  "aktueller_job": "Vertriebstrainer",
  "branche": "Versicherung"
}
```

### POST /api/assessment/answer
Schickt eine Antwort.
```json
{
  "session_id": "uuid",
  "frage_nr": 1,
  "antwort": "B",
  "reaction_time_ms": 4500
}
```

### POST /api/assessment/continue
Nach einem Magie-Moment weitermachen.
```json
{
  "session_id": "uuid"
}
```

### GET /api/health
Health Check.

### GET /api/session/{session_id}
Session-Status (Debug).
