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