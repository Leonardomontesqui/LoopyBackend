import requests
import os
import json
from fastapi import HTTPException, Query
from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool, OpenAIChatCompletionsModel
from openai import OpenAI
from . import database
# from agents.models.openai import OpenAIChatCompletionsModel
# from agents.tools import function_tool

load_dotenv(override=True)

api_key = os.getenv('POSTHOG_API_KEY') 
project_api_key = os.getenv('POSTHOG_PROJECT_API_KEY')
project_id = os.getenv('POSTHOG_PROJECT_ID')
gemini_api_key = os.getenv('GEMINI_API_KEY')

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


os.environ['OPENAI_API_KEY'] = gemini_api_key
os.environ['OPENAI_BASE_URL'] = GEMINI_BASE_URL


gemini_client = OpenAI(
    api_key=gemini_api_key,
    base_url=GEMINI_BASE_URL
)


gemini_model = OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=gemini_client)

@function_tool
def analyze_session_errors(errors: list) -> dict:
    """Analyze JavaScript console errors and generate a title and description for a bug report"""
    error_summary = "\n".join([f"- {error['message']} (occurred {error['count']} times)" for error in errors])
    
    prompt = f"""
    Analyze these JavaScript console errors from a user session and create:
    1. A concise, descriptive title (max 60 characters)
    2. A detailed description explaining what went wrong and potential impact
    
    Errors:
    {error_summary}
    
    Please respond with a JSON object in this exact format:
    {{
        "title": "Your concise title here",
        "description": "Your detailed description here"
    }}
    
    Make sure the title is under 60 characters and the description provides actionable insights for developers.
    """
    
    return {"prompt": prompt, "errors_count": len(errors)}

def create_analysis_agent():
    """Create an agent for analyzing session errors using Gemini API"""
    analysis_instructions = """You are an expert at analyzing JavaScript console errors and creating clear, actionable titles and descriptions for bug reports. Focus on the most impactful errors and provide insights that would help developers understand and fix the issues. MAX 2 SENTENCES
    
    Use the analyze_session_errors tool to process the errors and generate appropriate titles and descriptions."""
    
    analysis_agent = Agent(
        name="Session Error Analyzer", 
        instructions=analysis_instructions, 
        model=gemini_model
    )
    
    return analysis_agent

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

def get_recordings(limit: int = 100):
    return {"message": "Not implemented"}

def enable_session_sharing(session_id: str):
    """Enable sharing for a session replay using PostHog API"""
    if not session_id:
        raise HTTPException(400, "Session ID is required")
    

    url = f"https://us.posthog.com/api/projects/{project_id}/session_recordings/{session_id}/sharing"
    
    personal_api_key = api_key
    project_api_key = os.getenv('POSTHOG_PROJECT_API_KEY')
    

    params = {"personal_api_key": personal_api_key}
    
    print(f"Debug - Project ID: {project_id}")
    print(f"Debug - Personal API Key: {personal_api_key[:10]}...")
    print(f"Debug - Project API Key: {project_api_key[:10] if project_api_key else 'None'}...")
    print(f"Debug - URL: {url}")
    
    try:
        response = requests.patch(
            url,
            params=params,
            json={"enabled": True},
            headers={"Content-type": "application/json"}
        )
        
        print(f"Debug - Response Status: {response.status_code}")
        print(f"Debug - Response Headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"Debug - Response Text: {response.text}")
            
        response.raise_for_status()
        
        result = response.json()
        access_token = result.get('access_token')
        
        if access_token:

            iframe_code = f'<iframe allowfullscreen width="100%" height="450" frameborder="0" src="https://app.posthog.com/embedded/{access_token}"></iframe>'
            
            return {
                "session_id": session_id,
                "access_token": access_token,
                "embed_url": f"https://app.posthog.com/embedded/{access_token}",
                "iframe_code": iframe_code,
                "status": "sharing_enabled"
            }
        else:
            return {
                "session_id": session_id,
                "error": "No access token received",
                "response": result
            }
            
    except requests.exceptions.RequestException as e:

        if "403" in str(e) and project_api_key:
            print("Trying with project API key...")
            params = {"personal_api_key": project_api_key}
            
            try:
                response = requests.patch(
                    url,
                    params=params,
                    json={"enabled": True},
                    headers={"Content-type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                access_token = result.get('access_token')
                
                if access_token:
                    iframe_code = f'<iframe allowfullscreen width="100%" height="450" frameborder="0" src="https://app.posthog.com/embedded/{access_token}"></iframe>'
                    
                    return {
                        "session_id": session_id,
                        "access_token": access_token,
                        "embed_url": f"https://app.posthog.com/embedded/{access_token}",
                        "iframe_code": iframe_code,
                        "status": "sharing_enabled_with_project_key"
                    }
            except requests.exceptions.RequestException as e2:
                raise HTTPException(status_code=500, detail=f"Both API keys failed. Personal key error: {str(e)}, Project key error: {str(e2)}")
        
        raise HTTPException(status_code=500, detail=f"Failed to enable sharing: {str(e)}")

def get_session_share_info(session_id: str):
    """Get sharing information for a session replay"""
    if not session_id:
        raise HTTPException(400, "Session ID is required")
    

    url = f"https://us.posthog.com/api/projects/{project_id}/session_recordings/{session_id}/sharing"
    params = {"personal_api_key": api_key}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        result = response.json()
        access_token = result.get('access_token')
        
        if access_token:
            iframe_code = f'<iframe allowfullscreen width="100%" height="450" frameborder="0" src="https://app.posthog.com/embedded/{access_token}"></iframe>'
            
            return {
                "session_id": session_id,
                "access_token": access_token,
                "embed_url": f"https://app.posthog.com/embedded/{access_token}",
                "iframe_code": iframe_code,
                "sharing_enabled": True
            }
        else:
            return {
                "session_id": session_id,
                "sharing_enabled": False,
                "message": "Sharing not enabled for this session"
            }
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sharing info: {str(e)}")

def check_session_sharing_status(session_id: str):
    """Check if sharing is already enabled for a session"""
    if not session_id:
        raise HTTPException(400, "Session ID is required")
    
    url = f"https://us.posthog.com/api/projects/{project_id}/session_recordings/{session_id}/sharing"
    params = {"personal_api_key": api_key}
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            access_token = result.get('access_token')
            
            if access_token:
                iframe_code = f'<iframe allowfullscreen width="100%" height="450" frameborder="0" src="https://app.posthog.com/embedded/{access_token}"></iframe>'
                
                return {
                    "session_id": session_id,
                    "sharing_enabled": True,
                    "access_token": access_token,
                    "embed_url": f"https://app.posthog.com/embedded/{access_token}",
                    "iframe_code": iframe_code
                }
            else:
                return {
                    "session_id": session_id,
                    "sharing_enabled": False,
                    "message": "Sharing not enabled for this session"
                }
        else:
            return {
                "session_id": session_id,
                "sharing_enabled": False,
                "error": f"API returned status {response.status_code}",
                "message": "You may need to enable sharing manually in PostHog dashboard first",
                "instructions": [
                    "1. Go to PostHog dashboard",
                    "2. Find this session recording",
                    "3. Click 'Share' button",
                    "4. Enable external sharing",
                    "5. Copy the access token",
                    "6. Use that token in your embed"
                ]
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "session_id": session_id,
            "sharing_enabled": False,
            "error": str(e),
            "message": "API key may not have sharing permissions",
            "api_key_help": {
                "personal_api_key": "You need a Personal API Key with sharing permissions",
                "how_to_get": "Go to PostHog Settings > API Keys > Create Personal API Key",
                "permissions": "Make sure the key has 'Session Recordings' and 'Sharing' permissions"
            }
        }
    
async def analyze_recordings_for_errors():
    """
    The main workflow, now with AI agent analysis for titles and descriptions.
    """
    print("Starting analysis...")
    all_recordings_response = get_session_recordings()
    all_recordings = all_recordings_response.get('results', [])
    print(f"Found {len(all_recordings)} total recordings.")

    if not all_recordings:
        return []

    recordings_with_errors = [
        rec for rec in all_recordings if rec.get('console_error_count', 0) > 0
    ]
    print(f"Found {len(recordings_with_errors)} recordings with console_error_count > 0.")

    if not recordings_with_errors:
        return []
    
    simplified_error_sessions = []
    
    for recording in recordings_with_errors:
        session_id = recording.get('id')
        if not session_id:
            continue

        print(f"--- Processing session: {session_id} ---")

        error_messages = get_errors_for_session(session_id=session_id)
        print(f"Found {len(error_messages)} raw error messages for this session.")

        if not error_messages:
            print("No error messages found, skipping.")
            continue

        share_info = enable_session_sharing(session_id)
        
        error_counts = {}
        for message in error_messages:
            if message:
                error_counts[message] = error_counts.get(message, 0) + 1
        
        unique_errors = [
            {"message": msg, "count": count} for msg, count in error_counts.items()
        ]
        
        if not unique_errors:
            print(f"No unique errors could be parsed for session {session_id}, skipping.")
            continue

        # Use AI agent to generate title and description
        print(f"Generating AI analysis for session {session_id}...")
        try:
            # Use direct Gemini API call since it's more reliable
            ai_analysis = direct_gemini_analysis(unique_errors)
            print(f"AI analysis completed for session {session_id}")
        except Exception as e:
            print(f"AI analysis failed for session {session_id}: {e}")
            ai_analysis = {
                "title": f"Session {session_id} - Console Errors",
                "description": f"Session with {len(unique_errors)} different types of console errors."
            }

        session_object = {
            "session_id": session_id,
            "errors": unique_errors,
            "embed_url": share_info.get('embed_url'),
            "title": ai_analysis.get('title', f"Session {session_id} - Console Errors"),
            "description": ai_analysis.get('description', f"Session with console errors."),
            "start_time": recording.get('start_time'),
            "end_time": recording.get('end_time')
        }
        simplified_error_sessions.append(session_object)

        # Save the processed session to the database
        database.save_processed_session(session_object)
        
    print("Analysis complete.")
    return simplified_error_sessions

def get_errors_for_session(session_id: str) -> list:
    """
    A corrected, lean function to get only the error messages for a single session.
    This version correctly filters by event properties and parses the error message.
    """
    if not api_key or not project_id:
        raise HTTPException(400, "Missing PostHog credentials")

    url = f"https://us.posthog.com/api/projects/{project_id}/events/"
    headers = {"Authorization": f"Bearer {api_key}"}
    

    properties_filter = f'[{{"key": "$session_id", "value": "{session_id}", "operator": "exact", "type": "event"}}]'
    params = {
        "event": "$exception",
        "properties": properties_filter,
        "limit": 500
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        results = response.json().get('results', [])
        
        error_messages = []
        for event in results:
            props = event.get('properties', {})
            msg = None
            exc_list = props.get("$exception_list")
            if isinstance(exc_list, list) and exc_list:
                msg = exc_list[0].get("value")
            else:
                vals = props.get("$exception_values")
                msg = vals[0] if isinstance(vals, list) and vals else None
            
            if msg:
                error_messages.append(msg)
        
        return error_messages

    except requests.exceptions.RequestException as e:
        print(f"Error fetching events for session {session_id}: {e}")
        return []

def direct_gemini_analysis(errors: list) -> dict:
    """Direct Gemini API call as fallback when agents library fails"""
    error_summary = "\n".join([f"- {error['message']} (occurred {error['count']} times)" for error in errors])
    
    prompt = f"""
    Analyze these JavaScript console errors from a user session and create:
    1. A concise, descriptive title (max 60 characters)
    2. A detailed description explaining what went wrong and potential impact
    
    Errors:
    {error_summary}
    
    Please respond with a JSON object in this exact format:
    {{
        "title": "Your concise title here",
        "description": "Your detailed description here"
    }}
    
    Make sure the title is under 60 characters and the description provides actionable insights for developers.
    """
    
    try:
        response = gemini_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content
        
        # Try to parse as JSON
        try:
            if "{" in result_text and "}" in result_text:
                start = result_text.find("{")
                end = result_text.rfind("}") + 1
                json_str = result_text[start:end]
                return json.loads(json_str)
            else:
                return {
                    "title": "Session Console Errors",
                    "description": result_text
                }
        except json.JSONDecodeError:
            return {
                "title": "Session Console Errors",
                "description": result_text
            }
            
    except Exception as e:
        print(f"Direct Gemini API call failed: {e}")
        return {
            "title": "Session Console Errors",
            "description": f"Session with {len(errors)} different types of console errors."
        }