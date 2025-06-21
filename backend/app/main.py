from fastapi import FastAPI
from dotenv import load_dotenv
from agents import Agent, Runner, trace 
app = FastAPI()
load_dotenv(override=True)
import requests

import os


@app.get("/")
async def root():
    return {"message": "App running on fastapi"}

@app.get("/get-session-recordings")
async def get_session_recordings():
    api_key = os.getenv('POSTHOG_API_KEY') 
    project_id = os.getenv('POSTHOG_PROJECT_ID')
    response = requests.get(
        "https://us.posthog.com/api/projects/{project_id}/session_recordings/".format(
            project_id=project_id
        ),
        headers={"Authorization": "Bearer {}".format(api_key)},
    ).json()
    print(len(response['results']))
    return response
        
        
@app.get("/get-events")
async def get_events():
    api_key = os.getenv('POSTHOG_API_KEY') 
    project_id = os.getenv('POSTHOG_PROJECT_ID')
    
    response = requests.get(
    "https://us.posthog.com/api/projects/{project_id}/events/".format(
        project_id=project_id
    ),
    headers={"Authorization": "Bearer {}".format(api_key)},
    ).json()
    return response['results'][0]

@app.get("/get-recordings")
async def get_recordings():
    api_key = os.getenv('POSTHOG_API_KEY') 
    project_id = os.getenv('POSTHOG_PROJECT_ID')
    
    response = requests.get(
    "https://us.posthog.com/api/projects/{project_id}/session_recordings/".format(
        project_id=project_id
    ),
    headers={"Authorization": "Bearer {}".format(api_key)},
).json()

    return response['results'][0]



# @app.get("/test-posthog")
# async def test_posthog():
#     """Step 1.1: Test PostHog API and see the data structure"""
#     try:
#         api_key = os.getenv('POSTHOG_API_KEY') 
#         project_id = os.getenv('POSTHOG_PROJECT_ID')
        
#         response = requests.get(
#             "https://us.posthog.com/api/projects/{project_id}/session_recordings/".format(
#                 project_id=project_id
#             ),
#             headers={"Authorization": "Bearer {}".format(api_key)},
#         ).json()
        
#         # Show us what we're working with
#         return {
#             "status": "success",
#             "total_recordings": len(response.get('results', [])),
#             "sample_recording": response.get('results', [{}])[0] if response.get('results') else None,
#             "available_fields": list(response.get('results', [{}])[0].keys()) if response.get('results') else []
#         }
        
#     except Exception as e:
#         return {
#             "status": "error",
#             "error": str(e)
#         }
