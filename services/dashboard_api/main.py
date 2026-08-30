from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .database import connect

app = FastAPI(title="Control Tower API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "https://control-tower-tcp10.vercel.app",
        "https://frontend-eta-one-42.vercel.app",
        "https://frontend-bfizk72dq-tcp10.vercel.app",
    ],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


@contextmanager
def cursor():
    with connect() as connection:
        with connection.cursor() as db_cursor:
            yield db_cursor


class IncidentCreate(BaseModel):
    incident_key: str = Field(pattern=r"^[A-Z]+-\d+$")
    title: str
    severity: str
    overview: str
    country: str | None = None
    provider_name: str | None = None
    estimated_impact: float | None = None


class IncidentReadUpdate(BaseModel):
    is_read: bool


def serialize_incident(row):
    return {
        "key": row[0],
        "title": row[1],
        "severity": row[2],
        "status": row[3],
        "country": row[4],
        "provider": row[5],
        "overview": row[6],
        "estimatedImpact": row[7],
        "approvalRateDrop": row[8],
        "affectedTransactions": row[9],
        "agentAction": row[10],
        "agentActionAt": row[11],
        "startedAt": row[12],
        "lastSeenAt": row[13],
        "isRead": row[14],
    }


@app.get("/health")
def health():
    with cursor() as db_cursor:
        db_cursor.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/api/incidents")
def list_incidents():
    with cursor() as db_cursor:
        db_cursor.execute("""
            SELECT incident_key, title, severity, status, country, provider_name, overview,
                   estimated_impact, approval_rate_drop, affected_transaction_count, agent_action, agent_action_at,
                   started_at, last_seen_at, is_read
            FROM incidents ORDER BY CASE severity WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, last_seen_at DESC
        """)
        return [serialize_incident(row) for row in db_cursor.fetchall()]


@app.get("/api/dashboard/incidents-today")
def incidents_today():
    with cursor() as db_cursor:
        db_cursor.execute("""
            SELECT incident_key, severity
            FROM incidents
            WHERE started_at >= date_trunc('day', CURRENT_TIMESTAMP)
              AND started_at < date_trunc('day', CURRENT_TIMESTAMP) + INTERVAL '1 day'
            ORDER BY CASE severity WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, incident_key
        """)
        by_incident_key = [
            {"incidentKey": incident_key, "severity": severity, "count": 1}
            for incident_key, severity in db_cursor.fetchall()
        ]
    return {"total": len(by_incident_key), "byIncidentKey": by_incident_key}


@app.get("/api/dashboard/incidents-this-week")
def incidents_this_week():
    with cursor() as db_cursor:
        db_cursor.execute("""
            WITH days AS (
                SELECT generate_series(
                    date_trunc('week', CURRENT_DATE),
                    date_trunc('week', CURRENT_DATE) + INTERVAL '6 days',
                    INTERVAL '1 day'
                )::date AS day
            )
            SELECT days.day, COUNT(incidents.id)
            FROM days
            LEFT JOIN incidents
              ON incidents.started_at >= days.day
             AND incidents.started_at < days.day + INTERVAL '1 day'
            GROUP BY days.day
            ORDER BY days.day
        """)
        days = [
            {"date": day.isoformat(), "label": day.strftime("%a"), "count": count}
            for day, count in db_cursor.fetchall()
        ]
    return {"total": sum(item["count"] for item in days), "days": days}


@app.get("/api/incidents/{incident_key}")
def get_incident(incident_key: str):
    with cursor() as db_cursor:
        db_cursor.execute(
            """
            SELECT incident_key, title, severity, status, country, provider_name, overview,
                   estimated_impact, approval_rate_drop, affected_transaction_count, agent_action, agent_action_at,
                   started_at, last_seen_at, is_read
            FROM incidents WHERE incident_key = %s
        """,
            (incident_key,),
        )
        incident = db_cursor.fetchone()
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        return serialize_incident(incident)


@app.patch("/api/incidents/{incident_key}/read")
def update_incident_read_status(incident_key: str, update: IncidentReadUpdate):
    with cursor() as db_cursor:
        db_cursor.execute(
            """
            UPDATE incidents
            SET is_read = %s
            WHERE incident_key = %s
            RETURNING incident_key, title, severity, status, country, provider_name, overview,
                      estimated_impact, approval_rate_drop, affected_transaction_count, agent_action, agent_action_at,
                      started_at, last_seen_at, is_read
        """,
            (update.is_read, incident_key),
        )
        incident = db_cursor.fetchone()
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        return serialize_incident(incident)


@app.post("/api/incidents", status_code=201)
def create_incident(incident: IncidentCreate):
    with cursor() as db_cursor:
        db_cursor.execute(
            """
            INSERT INTO incidents (incident_key, title, severity, overview, country, provider_name, estimated_impact)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING incident_key
        """,
            (
                incident.incident_key,
                incident.title,
                incident.severity,
                incident.overview,
                incident.country,
                incident.provider_name,
                incident.estimated_impact,
            ),
        )
        return {"key": db_cursor.fetchone()[0]}
