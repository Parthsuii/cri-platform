from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="CRI Observability Dashboard", version="1.0.0")

# ── helpers ────────────────────────────────────────────────────────────────

def _pg_connect():
    """Connect to PostgreSQL using psycopg2 (available in env)."""
    try:
        import psycopg2
        import psycopg2.extras
        return psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "cri_runtime"),
            user=os.getenv("POSTGRES_USER", "cri_admin"),
            password=os.getenv("POSTGRES_PASSWORD", "supersecret"),
        ), psycopg2.extras
    except Exception:
        return None, None


def _qdrant_get(path: str) -> dict:
    url = f"http://localhost:6333{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return {}


# ── API endpoints ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "cri-dashboard"}


@app.get("/api/events")
def get_events(limit: int = 50):
    conn, extras = _pg_connect()
    if conn is None:
        return JSONResponse({"events": [], "error": "postgres_unavailable"})
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id::text, event_type, trace_id, payload, created_at::text "
                "FROM events ORDER BY created_at DESC LIMIT %s", (limit,)
            )
            rows = [dict(r) for r in cur.fetchall()]
        return {"events": rows}
    except Exception as e:
        return JSONResponse({"events": [], "error": str(e)})
    finally:
        conn.close()


@app.get("/api/checkpoints")
def get_checkpoints(limit: int = 30):
    conn, extras = _pg_connect()
    if conn is None:
        return JSONResponse({"checkpoints": [], "error": "postgres_unavailable"})
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id::text, trace_id, state_hash, object_key, created_at::text "
                "FROM checkpoints ORDER BY created_at DESC LIMIT %s", (limit,)
            )
            rows = [dict(r) for r in cur.fetchall()]
        return {"checkpoints": rows}
    except Exception as e:
        return JSONResponse({"checkpoints": [], "error": str(e)})
    finally:
        conn.close()


@app.get("/api/rollbacks")
def get_rollbacks(limit: int = 20):
    conn, extras = _pg_connect()
    if conn is None:
        return JSONResponse({"rollbacks": [], "error": "postgres_unavailable"})
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id::text, checkpoint_id::text, trace_id, status, reason, created_at::text "
                "FROM rollbacks ORDER BY created_at DESC LIMIT %s", (limit,)
            )
            rows = [dict(r) for r in cur.fetchall()]
        return {"rollbacks": rows}
    except Exception as e:
        return JSONResponse({"rollbacks": [], "error": str(e)})
    finally:
        conn.close()


@app.get("/api/metrics")
def get_metrics():
    conn, extras = _pg_connect()
    if conn is None:
        return JSONResponse({"metrics": {}, "error": "postgres_unavailable"})
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            total_events = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM events WHERE event_type='ACTION_PROPOSED'")
            proposed = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM rollbacks WHERE status='SUCCESS'")
            rollbacks = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM checkpoints")
            checkpoints = cur.fetchone()[0]
        return {
            "total_events": total_events,
            "actions_proposed": proposed,
            "successful_rollbacks": rollbacks,
            "checkpoints_created": checkpoints,
        }
    except Exception as e:
        return JSONResponse({"metrics": {}, "error": str(e)})
    finally:
        conn.close()


@app.get("/api/beliefs")
def get_beliefs():
    """Retrieve the first page of beliefs stored in Qdrant."""
    try:
        res = _qdrant_get("/collections/beliefs/points/scroll?limit=20&with_payload=true&with_vector=false")
        points = res.get("result", {}).get("points", [])
        beliefs = [
            {
                "id": p.get("id"),
                "belief": p.get("payload", {}).get("belief"),
                "confidence": p.get("payload", {}).get("confidence"),
                "category": p.get("payload", {}).get("metadata", {}).get("category"),
            }
            for p in points
        ]
        return {"beliefs": beliefs}
    except Exception as e:
        return JSONResponse({"beliefs": [], "error": str(e)})


@app.get("/api/dag")
def get_dag():
    """
    Build a lightweight checkpoint DAG from the checkpoints table.
    Nodes are checkpoints; edges link sequential checkpoints in the same trace.
    """
    conn, extras = _pg_connect()
    if conn is None:
        return JSONResponse({"nodes": [], "edges": [], "error": "postgres_unavailable"})
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id::text, trace_id, state_hash, created_at::text "
                "FROM checkpoints ORDER BY trace_id, created_at ASC LIMIT 100"
            )
            rows = [dict(r) for r in cur.fetchall()]

        nodes = [{"id": r["id"], "label": r["state_hash"][:10], "trace": r["trace_id"], "ts": r["created_at"]} for r in rows]

        # Group by trace and create sequential edges
        from collections import defaultdict
        trace_groups: dict = defaultdict(list)
        for r in rows:
            trace_groups[r["trace_id"]].append(r["id"])

        edges = []
        for trace_id, ids in trace_groups.items():
            for i in range(len(ids) - 1):
                edges.append({"from": ids[i], "to": ids[i + 1]})

        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        return JSONResponse({"nodes": [], "edges": [], "error": str(e)})
    finally:
        conn.close()


@app.get("/", response_class=HTMLResponse)
def dashboard():
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard HTML not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
