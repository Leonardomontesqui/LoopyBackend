import requests
import os
from fastapi import HTTPException, Query
from dotenv import load_dotenv
load_dotenv(override=True)

api_key = os.getenv('POSTHOG_API_KEY') 
project_id = os.getenv('POSTHOG_PROJECT_ID')

def get_session_recordings():
    response = requests.get(
        "https://us.posthog.com/api/projects/{project_id}/session_recordings/".format(
            project_id=project_id
        ),
        headers={"Authorization": "Bearer {}".format(api_key)},
    ).json()
    print(len(response['results']))
    return response

def get_events(session_id=None, limit=100):
    if not api_key or not project_id:
        raise HTTPException(400, "Missing POSTHOG_API_KEY or POSTHOG_PROJECT_ID")

    url = f"https://us.posthog.com/api/projects/{project_id}/events/"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"event": "$exception", "limit": limit}
    if session_id:
        params["properties.$session_id"] = session_id

    resp = requests.get(url, headers=headers, params=params)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise HTTPException(resp.status_code, f"PostHog API error: {e}")

    raw = resp.json().get("results", [])

    errors = []
    for ev in raw:
        props = ev.get("properties", {})
        # pull out the message
        msg = None
        exc_list = props.get("$exception_list")
        if isinstance(exc_list, list) and exc_list:
            msg = exc_list[0].get("value")
            stack = exc_list[0].get("stacktrace")
        else:
            vals = props.get("$exception_values")
            msg = vals[0] if isinstance(vals, list) and vals else None
            stack = props.get("$exception_stacktrace")

        errors.append({
            "event_id":   ev.get("id"),
            "timestamp":  ev.get("timestamp"),
            "session_id": props.get("$session_id"),
            "message":    msg,
            "stacktrace": stack
        })

    return {
        "requested_session": session_id,
        "fetched": len(errors),
        "errors": errors
    }

def get_recordings():
    response = requests.get(
    "https://us.posthog.com/api/projects/{project_id}/session_recordings/".format(
        project_id=project_id
    ),
    headers={"Authorization": "Bearer {}".format(api_key)},
).json()

    return response['results'][0] 