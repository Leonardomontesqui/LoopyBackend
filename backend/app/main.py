from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv
from agents import Agent, Runner, trace 
from . import posthog
app = FastAPI()
load_dotenv(override=True)

@app.get("/")
async def root():
    return {"message": "App running on fastapi"}

@app.get("/get-session-recordings")
async def get_session_recordings():
    return posthog.get_session_recordings()
        
@app.get("/get-events")
async def get_events(
    session_id: str | None = Query(
        None,
        description="(Optional) If set, only return errors from this session_id"
    ),
    limit: int = Query(
        100,
        ge=1, le=1000,
        description="How many error events to fetch (max 1000)"
    )
):
    return posthog.get_events(session_id=session_id, limit=limit)

@app.get("/get-recordings")
async def get_recordings():
    return posthog.get_recordings()

@app.get("/process-sessions-with-errors")
async def process_sessions_with_errors():
    """
    Analyzes all session recordings, finds ones with errors,
    and enriches them with event data and a shareable replay link.
    """
    return posthog.analyze_recordings_for_errors()

@app.post("/enable-session-sharing/{session_id}")
async def enable_session_sharing(session_id: str):
    """Enable sharing for a session replay and get embed code"""
    return posthog.enable_session_sharing(session_id)

@app.get("/get-session-share-info/{session_id}")
async def get_session_share_info(session_id: str):
    """Get sharing information for a session replay"""
    return posthog.get_session_share_info(session_id)

@app.get("/check-session-sharing/{session_id}")
async def check_session_sharing(session_id: str):
    """Check if sharing is enabled and get help if not"""
    return posthog.check_session_sharing_status(session_id)

