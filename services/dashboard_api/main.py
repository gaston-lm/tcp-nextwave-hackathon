import json
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    title: str
    severity: str
    overview: str
    dimension_signatures: dict[str, str | None]
    estimated_impact: float | None = None


class IncidentReadUpdate(BaseModel):
    is_read: bool


def serialize_incident(row):
    signature = row[5] if isinstance(row[5], dict) else json.loads(row[5])
    return {
        "key": row[0],
        "title": row[1],
        "severity": row[2],
        "status": row[3],
        "country": signature.get("country"),
        "provider": signature.get("provider"),
        "dimensionSignatures": signature,
        "overview": row[4],
        "estimatedImpact": row[6],
        "approvalRateDrop": row[7],
        "affectedTransactions": row[8],
        "agentAction": None,
        "agentActionAt": None,
        "startedAt": row[9],
        "lastSeenAt": row[10],
        "isRead": row[11],
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
            SELECT incident_id, title, severity, status, overview, dimension_signatures::text,
                   estimated_impact, approval_rate_drop, affected_transaction_count, started_at, last_seen_at, is_read
            FROM incidents ORDER BY CASE severity WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, last_seen_at DESC
        """)
        return [serialize_incident(row) for row in db_cursor.fetchall()]


@app.get("/api/dashboard/incidents-today")
def incidents_today():
    with cursor() as db_cursor:
        db_cursor.execute("""
            SELECT incident_id, severity
            FROM incidents
            WHERE started_at >= date_trunc('day', CURRENT_TIMESTAMP)
              AND started_at < date_trunc('day', CURRENT_TIMESTAMP) + INTERVAL '1 day'
            ORDER BY CASE severity WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, incident_id
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
            SELECT days.day, COUNT(incidents.incident_id)
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


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: int):
    with cursor() as db_cursor:
        db_cursor.execute(
            """
            SELECT incident_id, title, severity, status, overview, dimension_signatures::text,
                   estimated_impact, approval_rate_drop, affected_transaction_count, started_at, last_seen_at, is_read
            FROM incidents WHERE incident_id = %s
        """,
            (incident_id,),
        )
        incident = db_cursor.fetchone()
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        return serialize_incident(incident)


@app.patch("/api/incidents/{incident_id}/read")
def update_incident_read_status(incident_id: int, update: IncidentReadUpdate):
    with cursor() as db_cursor:
        db_cursor.execute(
            """
            UPDATE incidents
            SET is_read = %s
            WHERE incident_id = %s
            RETURNING incident_id, title, severity, status, overview, dimension_signatures::text,
                      estimated_impact, approval_rate_drop, affected_transaction_count, started_at, last_seen_at, is_read
        """,
            (update.is_read, incident_id),
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
            INSERT INTO incidents (title, severity, overview, dimension_signatures, estimated_impact)
            VALUES (%s, %s, %s, %s::jsonb, %s)
            RETURNING incident_id
        """,
            (
                incident.title,
                incident.severity,
                incident.overview,
                json.dumps(incident.dimension_signatures),
                incident.estimated_impact,
            ),
        )
        return {"key": db_cursor.fetchone()[0]}
