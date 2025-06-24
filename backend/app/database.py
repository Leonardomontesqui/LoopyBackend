import os
from typing import List, Dict
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(override=True)

# Supabase configuration
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)

# Database functions
def save_recording(recording_data: Dict):
    """Save a recording to Supabase"""
    try:
        result = supabase.table('recordings').insert({
            'id': recording_data.get('id'),
            'session_id': recording_data.get('session_id'),
            'duration': recording_data.get('duration'),
            'data': recording_data
        }).execute()
        return result
    except Exception as e:
        print(f"Error saving recording: {e}")
        return None

def get_recordings_from_db() -> List[Dict]:
    """Get all recordings from Supabase"""
    try:
        result = supabase.table('recordings').select('*').execute()
        return result.data
    except Exception as e:
        print(f"Error getting recordings: {e}")
        return []

def get_recording_by_id(recording_id: str) -> Dict:
    """Get a specific recording by ID"""
    try:
        result = supabase.table('recordings').select('*').eq('id', recording_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error getting recording: {e}")
        return None

def update_recording(recording_id: str, updates: Dict):
    """Update a recording in Supabase"""
    try:
        result = supabase.table('recordings').update(updates).eq('id', recording_id).execute()
        return result
    except Exception as e:
        print(f"Error updating recording: {e}")
        return None

def delete_recording(recording_id: str):
    """Delete a recording from Supabase"""
    try:
        result = supabase.table('recordings').delete().eq('id', recording_id).execute()
        return result
    except Exception as e:
        print(f"Error deleting recording: {e}")
        return None

def get_all_recordings():
    """Get all recordings from Supabase"""
    try:
        result = supabase.table('recordings').select('*').execute()
        return result
    except Exception as e:
        print(f"Error getting recordings: {e}")
        return None

def save_processed_session(session_data: Dict):
    """Saves the analyzed session data to the 'posthog' table using an upsert."""
    try:

        error_tags = [error['message'] for error in session_data.get('errors', [])]

        data_to_insert = {
            'video_link': session_data.get('embed_url'),
            'session_id': session_data.get('session_id'),
            'error_tags': error_tags,
            'title': session_data.get('title'),
            'description': session_data.get('description'),
            'start_time': session_data.get('start_time'),
            'end_time': session_data.get('end_time')
        }


        data_to_insert = {k: v for k, v in data_to_insert.items() if v is not None}
        

        result = supabase.table('posthog').upsert(
            data_to_insert, 
            on_conflict='session_id'
        ).execute()
        
        if result.data:
            print(f"Successfully upserted session {session_data.get('session_id')} to Supabase.")
        else:
             print(f"Upsert call for session {session_data.get('session_id')} returned no data, which may indicate an issue.")
        
        return result
    except Exception as e:
        print(f"--- FAILED to upsert session {session_data.get('session_id')} ---")
        print(f"REASON: {e}")
        print("----------------------------------------------------")
        return None

def get_session_by_id(session_id: str) -> Dict:
    """Get a specific session by session_id from the posthog table"""
    try:
        result = supabase.table('posthog').select('*').eq('session_id', session_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error getting session {session_id}: {e}")
        return None

def session_exists(session_id: str) -> bool:
    """Check if a session already exists in the database"""
    try:
        result = supabase.table('posthog').select('session_id').eq('session_id', session_id).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"Error checking if session {session_id} exists: {e}")
        return False 