import requests
import os
from fastapi import HTTPException, Query
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv('POSTHOG_API_KEY') 
project_api_key = os.getenv('POSTHOG_PROJECT_API_KEY')
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

def get_recordings(limit: int = 100):
    return {"message": "Not implemented"}

def enable_session_sharing(session_id: str):
    """Enable sharing for a session replay using PostHog API"""
    if not session_id:
        raise HTTPException(400, "Session ID is required")
    
    # According to PostHog docs: https://us.posthog.com/api/projects/{projectID}/session_recordings/{sessionID}/sharing?personal_api_key={POSTHOG_PERSONAL_API_KEY}
    url = f"https://us.posthog.com/api/projects/{project_id}/session_recordings/{session_id}/sharing"
    
    # Try both API keys to see which one works
    personal_api_key = api_key
    project_api_key = os.getenv('POSTHOG_PROJECT_API_KEY')
    
    # Use personal_api_key as query parameter, not in Authorization header
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
            # Create embed iframe code
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
        # Try with project API key if personal API key fails
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
    
    # Get sharing info via PostHog API
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