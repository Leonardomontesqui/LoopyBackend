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
