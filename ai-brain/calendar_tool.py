import datetime
import os.path
import uuid
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Shows basic usage of the Google Calendar API."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                if os.path.exists('token.json'):
                    os.remove('token.json')
                return get_calendar_service()
        else:
            if not os.path.exists('credentials.json'):
                print("❌ Error: credentials.json not found.")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def is_slot_free(service, start_dt, end_dt):
    """
    Checks if a time slot is free on the primary calendar.
    Returns True if free, False if busy.
    """
    try:
        # Convert to ISO format with 'Z' for UTC (Google requires this)
        time_min = start_dt.isoformat() + 'Z'
        time_max = end_dt.isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # If list is empty, the slot is free!
        if not events:
            return True
            
        print(f"⚠️ Slot {start_dt.strftime('%H:%M')} is busy. Conflict with: {events[0]['summary']}")
        return False
    except Exception as e:
        print(f"Error checking availability: {e}")
        return True # Assume free on error to prevent crashes

def create_meeting(summary, description, start_time_str, duration_minutes=60, is_video_call=False, strict_time=False):
    """
    Creates a meeting.
    - If strict_time=True: Only books at the exact requested time. Returns error if busy.
    - If strict_time=False: Auto-finds next free slot if requested time is busy.
    
    Args:
        summary: Meeting title
        description: Meeting description
        start_time_str: ISO format datetime string
        duration_minutes: Meeting duration (default 60)
        is_video_call: If True, adds Google Meet link
        strict_time: If True, only books at exact time (no auto-reschedule)
    """
    service = get_calendar_service()
    if not service:
        return "Error: Google Calendar not connected."

    try:
        # Parse the requested start time
        original_start = datetime.datetime.fromisoformat(start_time_str)
        current_start = original_start
        
        # Check if requested slot is free
        current_end = current_start + datetime.timedelta(minutes=duration_minutes)
        
        if is_slot_free(service, current_start, current_end):
            # Requested slot is free - use it!
            found_slot = True
        elif strict_time:
            # User specified exact time and it's busy - return error
            return f"Error: The requested time slot ({original_start.strftime('%I:%M %p')}) is already busy. Please choose another time."
        else:
            # Auto-reschedule: Try up to 10 slots (10 hours) to find a free one
            found_slot = False
            for _ in range(10):
                current_end = current_start + datetime.timedelta(minutes=duration_minutes)
                
                if is_slot_free(service, current_start, current_end):
                    found_slot = True
                    break
                else:
                    # If busy, add 1 hour and try again
                    current_start += datetime.timedelta(hours=1)
            
            if not found_slot:
                return "Error: Could not find a free slot today (Calendar is full)."

        # Create the event at the NEW found time
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': current_start.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': current_end.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
        }
        if is_video_call:
            event['conferenceData'] = {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }

        created_event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1).execute()
        
        final_time_str = current_start.strftime('%I:%M %p')
        
        # 5. Return correct link based on type
        if is_video_call:
            link = created_event.get('hangoutLink', 'No Meet Link')
        else:
            link = created_event.get('htmlLink', 'No Calendar Link')
            
        return f"Success! Link: {link} (Booked at {final_time_str})"

    except Exception as e:
        return f"Failed: {str(e)}"
def check_availability(start_time_str, duration_minutes=60):
    """
    Exposed helper for server.py to check if a slot is free.
    """
    service = get_calendar_service()
    if not service: return False, "Calendar not connected"

    try:
        clean_time = start_time_str.replace("Z", "")
        start_dt = datetime.datetime.fromisoformat(clean_time)
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
        
        # We reuse the is_slot_free logic you already have
        is_free = is_slot_free(service, start_dt, end_dt)
        
        if is_free:
            return True, "Available"
        else:
            return False, "Busy"
    except Exception as e:
        return False, f"Error: {e}"

def find_next_free_slot(start_time_str, duration_minutes=60, max_hours_ahead=8):
    """
    Finds the next available free slot.
    """
    service = get_calendar_service()
    if not service: return False, None, "No Calendar", []
    
    try:
        clean_time = start_time_str.replace("Z", "")
        start_dt = datetime.datetime.fromisoformat(clean_time)
        skipped_slots = []
        
        for i in range(1, max_hours_ahead + 1):
            next_slot = start_dt + datetime.timedelta(hours=i)
            
            # Working hours logic (9 AM - 6 PM)
            if 9 <= next_slot.hour < 18:
                next_iso = next_slot.isoformat()
                end_slot = next_slot + datetime.timedelta(minutes=duration_minutes)
                
                # Check this slot
                if is_slot_free(service, next_slot, end_slot):
                    readable = next_slot.strftime('%A at %I:%M %p')
                    return True, next_iso, readable, skipped_slots
                else:
                    skipped_slots.append({
                        "time": next_slot.strftime('%I:%M %p'),
                        "conflict": "Busy"
                    })
                    
        return False, None, "No slots found", skipped_slots

    except Exception as e:
        print(f"Find error: {e}")
        return False, None, str(e), []