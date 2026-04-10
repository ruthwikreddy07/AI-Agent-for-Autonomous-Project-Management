# server.py  -- Combined Option A (HF embeddings, no sentence_transformers)
import os
import json
import requests
import time as time_module
from typing import List, Dict, Any
from collections import Counter, defaultdict  # Needed for counting tasks
from pydantic import BaseModel
import random 
from graphlib import TopologicalSorter
from datetime import datetime, timedelta, time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from pymongo import MongoClient
from passlib.context import CryptContext
from jose import jwt
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from pinecone import Pinecone
from dotenv import load_dotenv
import google.generativeai as genai  # <--- NEW IMPORT

# --- calendar_tool import (optional) ---
try:
    # Ensure check_availability and find_next_free_slot are exposed in your calendar_tool.py
    from calendar_tool import create_meeting, check_availability,find_next_free_slot
except ImportError:
    print("⚠️ Warning: calendar_tool.py not found. Scheduling will not work.")
    def create_meeting(*args, **kwargs): return "Error: calendar_tool.py missing"
    def check_availability(*args, **kwargs): return False, "calendar_tool.py missing"
    def find_next_free_slot(*args, **kwargs): return False, None, "calendar_tool.py missing", []

load_dotenv()

# --------------------
# CONFIG & SECRETS
# --------------------
# --------------------
# 📅 CALENDAR CONFIG
# --------------------
COMPANY_HOLIDAYS = [
    "2025-12-25", "2026-01-01", "2026-01-26" 
]
WEEKEND_DAYS = [5, 6]  # Saturday=5, Sunday=6
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_HOST = os.getenv("PINECONE_HOST")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret")
ALGORITHM = "HS256"
DEFAULT_OWNER = os.getenv("DEFAULT_OWNER", "")

N8N_TRELLO_URL = os.getenv("N8N_TRELLO_URL")
N8N_SLACK_URL = os.getenv("N8N_SLACK_URL")
N8N_GET_CARDS_URL = os.getenv("N8N_GET_CARDS_URL")
N8N_ALERT_URL = os.getenv("N8N_ALERT_URL")
N8N_GET_ALL_CARDS_URL = os.getenv("N8N_GET_ALL_CARDS_URL")

TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")

TRELLO_LABELS = {
    "bug": os.getenv("PASTE_RED_LABEL_ID"),
    "feature": os.getenv("PASTE_GREEN_LABEL_ID"),
    "urgent": os.getenv("PASTE_YELLOW_LABEL_ID"),
}

# expose GROQ key if used by the llm library
if GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# ---------------------------
# EMBEDDING CONFIGURATION
# ---------------------------
HF_TOKEN = os.getenv("HF_TOKEN")

# 🔥 FIX 1: Use the new router endpoint (api-inference is deprecated)
HF_API_URL = "https://router.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------
# EMBEDDING CONFIGURATION (GOOGLE GEMINI)
# ---------------------------
# Make sure GOOGLE_API_KEY is in your .env file
# --- 🚀 CORRECTED: Using gemini-embedding-001 ---
def generate_embedding(text: str):
    model_id = "gemini-embedding-001" # The new stable 2026 model
    api_key = os.getenv("GOOGLE_API_KEY")
    
    # Updated URL to use the correct model ID
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:embedContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "model": f"models/{model_id}", # Correct model string
        "content": {"parts": [{"text": text}]}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        raise Exception(f"Gemini API Error: {response.text}")
        
    return response.json()['embedding']['values']
# durations for due date heuristics
DURATION_RULES = {"ui": 3, "design": 3, "api": 5, "database": 4, "test": 2, "deploy": 1, "fix": 1, "meeting": 0}

# --------------------
# APP & CORS
# --------------------
app = FastAPI()

# adjust allowed origins per your frontend (Render)
allowed_origins = [
    "http://localhost:4200",
    "https://ai-agent-for-project-management.onrender.com",
    "https://ai-agent-for-project-management.onrender.com/" # Add both with and without slash
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # Explicitly list methods
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"], # Be explicit
    expose_headers=["*"],
)

# ensure CORS headers on unexpected exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": allowed_origins[0] if allowed_origins else "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# --------------------
# DATABASE (pymongo)
# --------------------
client = None
db = None
users_collection = None
employees_collection = None
time_logs_collection = None
projects_collection = None
epics_collection = None
stories_collection = None
tasks_collection = None
sprints_collection = None
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["ai_project_manager"]
    users_collection = db["users"]
    employees_collection = db["employees"]
    chats_collection = db["chats"]
    time_logs_collection = db["time_logs"]
    projects_collection = db["projects"]
    epics_collection = db["epics"]
    stories_collection = db["stories"]
    tasks_collection = db["tasks"]
    sprints_collection = db["sprints"]
    client.admin.command("ping")
    print("✅ Connected to MongoDB")
except Exception as e:
    print("❌ MongoDB Error:", e)

# --------------------
# SECURITY & MODELS
# --------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

from models import *
from bson import ObjectId



# --------------------
# MEMORY & LLM
# --------------------
pc = Pinecone(api_key=PINECONE_API_KEY)
memory_index = pc.Index(name="project-memory", host=PINECONE_HOST)
llm = ChatGroq(model="llama-3.1-8b-instant",api_key=GROQ_API_KEY)

# --------------------
# HELPERS
# --------------------

def calculate_smart_timeline(tasks):
    """
    Sorts tasks by dependency and calculates dates skipping weekends/holidays.
    Updates the description with Blocked By and Timeline info.
    Includes FUZZY MATCHING and SEQUENTIAL FALLBACK.
    """
    # 0. Normalize tasks (Handle strings vs dicts to prevent crashes)
    normalized_tasks = []
    for t in tasks:
        if isinstance(t, str):
            normalized_tasks.append({"name": t, "desc": "Auto-generated", "depends_on": []})
        elif isinstance(t, dict):
            normalized_tasks.append(t)
    tasks = normalized_tasks

    # 1. Preparation
    graph = {}
    def clean(s): return str(s).lower().strip()
    
    # Build a map of clean_name -> task
    task_map = {}
    for t in tasks:
        if "name" in t:
            task_map[clean(t["name"])] = t

    # --- HELPER: Fuzzy Matcher ---
    def find_best_match(dep_name):
        c_dep = clean(dep_name)
        if c_dep in task_map: return c_dep
        # Try partial match (e.g. "Backend" matching "Build Backend")
        for t_name in task_map:
            if c_dep in t_name or t_name in c_dep:
                return t_name
        return None

    # 2. Build Graph & Resolve Dependencies
    for t in tasks:
        # Standardize Description
        if "desc" not in t: t["desc"] = t.get("description", "")
        if t["desc"] is None: t["desc"] = ""
            
        # Normalize Dependencies
        raw_deps = t.get("depends_on", [])
        
        # --- FIX: Handle case where AI returns a single string instead of a list ---
        if isinstance(raw_deps, str):
            raw_deps = [raw_deps]
            
        normalized_deps = []
        for d in raw_deps:
            if isinstance(d, dict) and "name" in d: normalized_deps.append(d["name"])
            elif isinstance(d, str): normalized_deps.append(d)
        
        # Resolve clean names using Fuzzy Match
        final_deps = []
        for d in normalized_deps:
            match = find_best_match(d)
            if match:
                final_deps.append(match)
        
        # Save back specific dependencies for the topological sort
        t["depends_on"] = final_deps 
        graph[clean(t["name"])] = set(final_deps)

    # 3. --- FALLBACK: Sequential Logic ---
    # If the AI provided ZERO dependencies (Lazy AI), assume a step-by-step list.
    total_edges = sum(len(deps) for deps in graph.values())
    if total_edges == 0 and len(tasks) > 1:
        prev_clean = None
        prev_raw = None
        for t in tasks:
            curr_clean = clean(t["name"])
            if prev_clean and curr_clean in task_map:
                # Create a link: Previous -> Current
                graph[curr_clean].add(prev_clean)
                t["depends_on"].append(prev_clean) 
            prev_clean = curr_clean
            prev_raw = t["name"]

    # 4. Topological Sort
    try:
        sorter = TopologicalSorter(graph)
        ordered_clean_names = list(sorter.static_order())
    except Exception as e:
        print(f"⚠️ Cycle detected or sort error: {e}")
        ordered_clean_names = [clean(t["name"]) for t in tasks] # Fallback

    # 5. Date Calculation
    schedule = []
    completion_dates = {} 
    project_start = datetime.now()

    for clean_name in ordered_clean_names:
        if clean_name not in task_map: continue
        task = task_map[clean_name]
        
        # Start Date Logic
        my_clean_deps = task.get("depends_on", [])
        dep_ends = [completion_dates[d] for d in my_clean_deps if d in completion_dates]
        
        if dep_ends:
            start_date = max(dep_ends) + timedelta(days=1)
        else:
            start_date = project_start + timedelta(days=1)

        # Duration Logic
        days_needed = 2
        for k, v in DURATION_RULES.items():
            if k in task["name"].lower(): days_needed = max(days_needed, v)

        # Calendar Logic
        while start_date.weekday() in WEEKEND_DAYS or start_date.strftime("%Y-%m-%d") in COMPANY_HOLIDAYS:
            start_date += timedelta(days=1)

        current_date = start_date
        days_to_add = days_needed - 1  
        
        while days_to_add > 0:
            current_date += timedelta(days=1)
            if current_date.weekday() not in WEEKEND_DAYS and current_date.strftime("%Y-%m-%d") not in COMPANY_HOLIDAYS:
                days_to_add -= 1
        
        while current_date.weekday() in WEEKEND_DAYS or current_date.strftime("%Y-%m-%d") in COMPANY_HOLIDAYS:
            current_date += timedelta(days=1)
        
        # Save Data
        completion_dates[clean_name] = current_date
        task["start_date"] = start_date.strftime("%Y-%m-%d")
        task["due_date"] = current_date.strftime("%Y-%m-%d")
        task["duration"] = days_needed
        
        # Write to Description
        if task.get("depends_on"):
            # Convert clean names back to readable names
            readable_deps = [task_map[d]["name"] for d in task["depends_on"] if d in task_map]
            blocker_text = ', '.join(readable_deps)
            task["desc"] += f"\n\n🛑 **Blocked By:** {blocker_text}"
            
        task["desc"] += f"\n📅 **Timeline:** {task['start_date']} ➝ {task['due_date']}"
        
        schedule.append(task)

    return schedule

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Decodes the token to get the username."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return username
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

def get_current_user_with_role(token: str = Depends(oauth2_scheme)):
    """Decodes the token and returns (username, role) tuple."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "developer")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return {"username": username, "role": role}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

def require_role(*allowed_roles):
    """FastAPI dependency that checks if the user has the required role."""
    def role_checker(user_info: dict = Depends(get_current_user_with_role)):
        if user_info["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}. Your role: {user_info['role']}"
            )
        return user_info
    return role_checker

def get_trello_id_by_email(email: str) -> str:
    if not TRELLO_API_KEY or not TRELLO_TOKEN:
        return ""
    url = "https://api.trello.com/1/search/members/"
    try:
        resp = requests.get(url, params={"query": email, "key": TRELLO_API_KEY, "token": TRELLO_TOKEN, "limit": 1}, timeout=10)
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]["id"]
    except Exception:
        pass
    return ""

def get_dynamic_roster():
    try:
        employees = list(employees_collection.find({}, {"_id": 0}))
        if not employees:
            return "No employees found."
        roster = "TEAM ROSTER:\n"
        for emp in employees:
            roster += f"- {emp['name']} ({emp.get('role','')}) - Skills: {', '.join(emp.get('skills',[]))}\n"
        return roster
    except Exception:
        return "Error."

def auto_assign_owner(task_name: str, task_desc: str) -> str:
    """
    Assigns a task to an employee by matching skills OR role keywords.
    """
    text = (task_name + " " + task_desc).lower()
    
    try:
        employees = list(employees_collection.find({}, {"_id": 0}))
        
        # --- STRATEGY 1: Exact Skill Match ---
        # (e.g. Task has "React", Employee has "React")
        for emp in employees:
            for skill in emp.get("skills", []):
                clean_skill = skill.strip().lower()
                if clean_skill and clean_skill in text:
                    return emp["name"]
        
        # --- STRATEGY 2: Role Keyword Match ---
        # (e.g. Task has "Frontend", Employee Role is "Frontend Developer")
        common_roles = ["frontend", "backend", "ui", "ux", "designer", "qa", "devops", "security", "data", "mobile", "cloud"]
        
        for emp in employees:
            role = emp.get("role", "").lower()
            for keyword in common_roles:
                # If the keyword (e.g. "frontend") is in BOTH the role AND the task text
                if keyword in role and keyword in text:
                    return emp["name"]

        # --- STRATEGY 3: Workload-Aware Tiebreaker ---
        # If multiple matches found via skill, pick the least loaded
        if len(employees) > 1:
            try:
                response = requests.get(N8N_GET_ALL_CARDS_URL, timeout=10)
                if response.status_code == 200:
                    raw_data = response.json()
                    all_cards = raw_data if isinstance(raw_data, list) else raw_data.get("data", [])
                    trello_done_list = os.getenv("TRELLO_DONE_LIST_ID", "6922b7e358b2e5d625ad65ba")
                    
                    owner_counts = {}
                    for c in all_cards:
                        if isinstance(c, dict) and "json" in c: c = c["json"]
                        if not isinstance(c, dict): continue
                        if c.get("idList") == trello_done_list or c.get("dueComplete"): continue
                        card_name = c.get("name", "")
                        if "[" in card_name and "]" in card_name:
                            owner = card_name.split("]")[0].replace("[", "").strip()
                            owner_counts[owner] = owner_counts.get(owner, 0) + 1
                    
                    # Sort employees by least tasks
                    employees_sorted = sorted(employees, key=lambda e: owner_counts.get(e.get("name", ""), 0))
                    if employees_sorted:
                        return employees_sorted[0]["name"]
            except:
                pass

    except Exception as e:
        print(f"⚠️ Assignment Logic Error: {e}")
        pass
        
    return "Unassigned"

def get_default_owner():
    if DEFAULT_OWNER:
        return DEFAULT_OWNER
    try:
        first_emp = employees_collection.find_one({}, {"_id": 0, "name": 1})
        if first_emp and first_emp.get("name"):
            return first_emp["name"]
    except:
        pass
    return "Unassigned"

def get_active_workflow_count():
    """
    Fetches active workflows with an automatic retry logic 
    to handle Render cold-starts (ConnectionResetError).
    """
    api_key = os.getenv("N8N_API_KEY")
    base_url = os.getenv("N8N_BASE_URL")
    
    if not api_key or not base_url:
        print("⚠️ n8n API credentials missing in .env")
        return 0

    # Max retries = 3
    for attempt in range(3):
        try:
            # Use a fresh session for each major attempt
            with requests.Session() as session:
                session.headers.update({"X-N8N-API-KEY": api_key})
                
                # attempt 0: 15s, attempt 1: 30s, attempt 2: 45s
                timeout_val = 15 * (attempt + 1)
                
                response = session.get(f"{base_url}/workflows", timeout=timeout_val)
                
                if response.status_code == 200:
                    data = response.json()
                    workflows = data.get('data', [])
                    return sum(1 for wf in workflows if wf.get('active') is True)
                
                print(f"⚠️ n8n Attempt {attempt+1} failed with status {response.status_code}")
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"⏳ Render is waking up... Attempt {attempt+1} failed. Retrying in 3s...")
            time_module.sleep(3) # Wait 3 seconds before trying again
            
    return 0

def get_trello_id_from_db(name: str):
    try:
        emp = employees_collection.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if emp:
            return emp.get("trello_id", "")
    except:
        pass
    return ""

def estimate_due_date(task_name: str) -> str:
    days = 2
    for k, v in DURATION_RULES.items():
        if k in task_name.lower():
            days = max(days, v)
    return (datetime.now() + timedelta(days=days)).isoformat()

# --------------------
# SYSTEM PROMPT
# --------------------
chat_history = []
user_states = {}

def get_user_state(username: str):
    if username not in user_states:
        user_states[username] = {
            "pending_plan": None,
            "current_risks": [],
            "current_budget_warning": ""
        }
    return user_states[username]

def refresh_system_prompt():
    global chat_history
    roster = get_dynamic_roster()
    today_str = datetime.now().strftime("%Y-%m-%d (%A)")
    # Note: The JSON example below uses {{ and }} to escape them for the f-string
    prompt = f"""
You are an Intelligent AI Project Manager.
📅 TODAY'S DATE: {today_str}

{roster}

===========================
⚙️  TOOLKIT
===========================

1️⃣  **execute_project_plan**
    - 🚨 **PRIORITY TOOL**: - Use this when the user explicitly asks to CREATE a new plan or execution strategy.
     - Do NOT use this if the user just mentions "development" as a topic for a meeting.
    - Use this ONLY for COMPLEX requests.
    - Trigger words: "Build", "Create", "Launch", "Develop", "Plan".
    - **CRITICAL**: The 'tasks' argument MUST be a valid JSON string array.
    - Each item MUST be: {{ "name": "Task Title", "desc": "Short description", "owner": "Role Name", "depends_on": ["Task Name"] }}
    - "depends_on": List of task names that must finish BEFORE this one starts.
    - Example: "Build API" depends on ["Design Database"].
    - "tool_cost" is optional: Estimate price of tools/software/vendors (e.g., 50 for a license).
    - Argument 'goal': Short description of the project.
    - Argument 'budget': 
      - 🛑 STRICTLY extract the dollar amount from the user's prompt.
      - 🛑 IF NO CURRENCY AMOUNT IS MENTIONED IN THE CHAT: You MUST pass 0.
      - 🛑 DO NOT infer budget from document content unless explicitly told to "use the budget from the document".
      - If unsure, pass 0.
    - Argument 'tasks': A valid JSON string array of tasks.
    - **CRITICAL**: The 'tasks' argument MUST be a valid JSON string array
    - Every task MUST include:
     - title
     - assigned_to
     - deadline
     - focus_time (1-hour slot)
     - 🛑 DO NOT create separate tasks for "Create Trello Card". The system does this automatically.
     - Only list the actual project work (e.g., "Design API", "Test Login").
     - If the user does not explicitly mention a dollar amount (e.g. "$500"), you MUST pass 0 for 'budget'. Do not guess.
    - Requires human approval.

2️⃣  **create_task_in_trello**
    - Use ONLY for simple, single tasks.
    - Use this if the user reports a "bug", "issue", or asks to "send an email about a critical issue" (This triggers an urgent alert).

3️⃣  schedule_meeting_tool
    - 🚨 **HIGHEST PRIORITY**: If the user input contains "Schedule", "Book", or "Set up meeting", you MUST use this tool.
    - 🛑 **IF NO TIME IS PROVIDED**: Do NOT call the tool. Reply: "When would you like to schedule the meeting?"
    - 🛑 DO NOT use this tool for "sending emails" or "reporting bugs".
    - 🛑 DO NOT GUESS THE TIME.
    - 🛑 IGNORE the "Topic" for tool selection. (e.g., if user says "Schedule a meeting about Development", do NOT check development status. Just book the meeting).
    - 🛑 STEP 1: ALWAYS call with `action="check"` FIRST (never skip this step).
    - 🛑 STEP 2: Process the tool response:
      - If response says "✅ Available": Ask user "The time [TIME] is available. Would you like me to book it?"
      - If response says "⚠️ BUSY": The tool has found a NEW free slot. Ask user "The requested time is busy. I found a free slot at [NEW TIME]. Shall we book that?"
      - Both responses include instructions on what to do next - FOLLOW THEM.
    - 🛑 STEP 3 (CRITICAL): 
      - If the user says "YES" (or "book it", "sure", "ok") after you suggested a time:
        - **YOU MUST CALL THE TOOL `schedule_meeting_tool`**.
        - Arguments: `action="book"`, `start_time="THE_ISO_TIME"`, `summary="The Meeting Title"`.
        - **DO NOT** use `send_slack_announcement` for this.
        - 🛑 The tool AUTOMATICALLY notifies Slack. **DO NOT** call `send_slack_announcement`.
        - **DO NOT** just reply with text.
      - If the user says "NO", "Cancel", or "Don't":
        - Simply reply: "Okay, request cancelled."
        - **DO NOT** call any tools.
        - **DO NOT** try to find another time unless asked.


4️⃣  **check_project_status**
    - Use for project progress checks, risks, summaries
    - 🛑 DO NOT use if the user asks to "Schedule" or "Book" a meeting.

5️⃣  **consult_project_memory**
    - Use when user asks specific questions about project facts, summaries, or uploaded documents.
    - 🚨 **CRITICAL RULE**: If the user asks for a "summary", "details", or "context" of a file, you MUST call this tool.
    - 🛑 **NEVER** say "I haven't received a document" without trying this tool first.
    - 🛑 The document is in your MEMORY, not in the chat history. SEARCH FOR IT.

6️⃣  heal_project_schedule
    - Use when the user asks to "Heal", "Fix", "Repair", or "Reschedule" the project.
    - This tool automatically moves overdue tasks and resolves dependency conflicts in Trello.

7️⃣  **check_team_workload**
    - Use when user asks about team capacity, workload, bandwidth, or "who is free".
    - Trigger words: "workload", "capacity", "bandwidth", "who is free", "team load", "available".
    - Returns active task count per team member with status indicators.

8️⃣  **log_time**
    - Use when a user reports time spent on a task.
    - Trigger words: "spent", "worked", "logged", "hours on".
    - Example: "I spent 4 hours on the API task" → log_time(task_name="API task", hours=4)
    - Always confirm the logged time back to the user.

9️⃣  **send_deadline_alerts**
    - Use when user asks about upcoming deadlines, urgent tasks, or "what's due soon".
    - Trigger words: "deadlines", "due soon", "urgent tasks", "overdue", "alerts".
    - Default to checking 2 days ahead. Sends alert to Slack automatically.



===========================
📌  CRITICAL DECISION RULES
===========================

1. **COMPLEX REQUEST → execute_project_plan**
   Never create a single task for large requests.

2. **SIMPLE REQUEST → create_task_in_trello**
   Only tiny/single actionable tasks go here.

3. **APPROVAL FLOW**
   - Only `execute_project_plan` requires approval.
   - `create_task_in_trello` executes instantly.

4. **ASSIGNMENTS**
   - Always assign tasks to the RIGHT PERSON based on skills.
   - Use the roster above to decide.

5. **OUTPUT FORMAT**
   - DO NOT use XML tags like <function>.
   - ALWAYS call tools using JSON ONLY.
   - Tool inputs must be valid JSON inside the tool call.
===========================
RULES & OUTPUT
===========================
Every task MUST include:
- title
- assigned_to
- deadline
- focus_time (1-hour slot)

- IF user asks to "Plan", "Design", "Build": call execute_project_plan and produce mutiple subtasks.
- Assign owners using the team roster or DEFAULT_OWNER fallback.
- ALWAYS call tools using JSON only when invoked.
- Always think step-by-step.
- Always choose the correct tool.
- Never mix complex plans with simple tasks.
- Ensure clean JSON formatting.
- MEMORY USAGE:
  - If you use 'consult_project_memory', do NOT output the raw "Memory Findings".
  - Read the findings silently, then formulate a natural language answer for the user based on that data.

===========================
🛑  STRICT JSON RULE
===========================

When calling a tool:

- The FULL reply must be ONLY a JSON object.
- Do NOT add explanations, descriptions, or natural language.
- Do NOT wrap JSON in backticks.
- Do NOT include text before or after JSON.
- Output EXACTLY:

{{
    "tool_name": "<tool_name>",
    "arguments": "..."
}}

If you are not calling a tool, output normal text.
"""
    # This line MUST be indented to be part of the function
    chat_history = [SystemMessage(content=prompt)]

# initialize
refresh_system_prompt()

# --------------------
# TOOLS
# --------------------

def internal_create_trello(name, desc, owner, start_hour=10,specific_due_date=None):
    if specific_due_date:
        due_date = specific_due_date
    else:
        due_date = estimate_due_date(name)
    member_id = get_trello_id_from_db(owner)
    emp_email = "" 
    try:
        emp = employees_collection.find_one({"name": {"$regex": f"^{owner}$", "$options": "i"}})
        if emp: emp_email = emp.get("email", "")
    except: pass

    if not member_id and owner != "Unassigned":
        name = f"[{owner}] {name}"

    label_id = ""
    is_urgent = False
    name_lower = name.lower()

    # Check urgency independently of label logic
    if any(x in name_lower for x in ("critical", "urgent", "crash", "alert")): is_urgent = True

    # Fallback: If urgent but no email found (e.g. Unassigned), try default owner
    if is_urgent and not emp_email:
        def_owner = get_default_owner()
        if def_owner and def_owner != "Unassigned":
            try:
                def_emp = employees_collection.find_one({"name": {"$regex": f"^{def_owner}$", "$options": "i"}})
                if def_emp: emp_email = def_emp.get("email", "")
            except: pass

    if "bug" in name_lower or "fix" in name_lower:
        label_id = TRELLO_LABELS.get("bug", "")
    elif "feature" in name_lower:
        label_id = TRELLO_LABELS.get("feature", "")

    full_desc = f"👤 **ASSIGNED TO:** {owner}\n\n{desc}"
    payload = {"task_name": name, "description": full_desc,"desc": full_desc, "due_date": due_date, "member_id": member_id, "label_id": label_id}

    trello_success = False
    for attempt in range(3): # Try 3 times
        try:
            resp = requests.post(N8N_TRELLO_URL, json=payload, timeout=30)
            if resp.status_code == 200: 
                trello_success = True
                break # Success! Exit the loop
            else: 
                print(f"⚠️ Trello Fail (Attempt {attempt+1}): {resp.text}", flush=True)
        except Exception as e:
            print(f"⚠️ Trello Error (Attempt {attempt+1}): {e}", flush=True)
            time_module.sleep(2) # Wait 2 seconds before retrying
            
    calendar_msg = ""
    
    # Only proceed if Trello card created
    if trello_success:
        due_dt = datetime.fromisoformat(due_date)
        focus_start = (due_dt - timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
        focus_title = f"⚡ Focus Time: {name}"
        
        # --- 1. GOOGLE CALENDAR (Independent Block) ---
        clean_link = "Check Calendar"
        actual_time = "TBD"
        try:
            result = create_meeting(focus_title, f"Work on Trello Card: {name}", focus_start.isoformat(), is_video_call=False)
            
            if "Success" in str(result):
                # Try to clean link safely
                try: clean_link = str(result).split(" (Booked")[0].replace("Success! Link: ", "").strip()
                except: clean_link = str(result)

                actual_time = focus_start.strftime('%A at %I:%M %p')
                if "(Booked at " in str(result):
                    try: 
                        booked_time = str(result).split("(Booked at ")[1].replace(")", "")
                        actual_time = f"{focus_start.strftime('%A')} at {booked_time}"
                    except: pass
                calendar_msg = f" (📅 {actual_time})"
            else:
                print(f"⚠️ Calendar Warning: {result}", flush=True)
        except Exception as e:
            print(f"⚠️ Calendar Failed: {e}", flush=True)

        # --- 2. SLACK NOTIFICATION (Runs Separately) ---
        try:
            # Extract Budget from Description
            budget_line = ""
            if "💰" in desc:
                for line in desc.split('\n'):
                    if "💰" in line:
                        budget_line = f"\n{line}" 
                        break

            slack_msg = (
                f"📅 *AUTO-SCHEDULED:* {focus_title}\n"
                f"👤 *Assigned To:* {owner}\n"
                f"⏰ *Focus Time:* {actual_time}\n"
                f"🎯 *Deadline:* {due_dt.strftime('%Y-%m-%d')}"
                f"{budget_line}\n"
                f"🔗 *Calendar Link:* {clean_link}"
            )
            
            print(f"📤 Sending Slack for {name}...", flush=True)
            # Increased timeout to 10s to prevent early cutoffs
            requests.post(N8N_SLACK_URL, json={"message": slack_msg}, timeout=10)
            
            # Anti-flood delay (Important!)
            print("⏳ Waiting 2s...", flush=True)
            time_module.sleep(2) 
            
        except Exception as e:
            print(f"❌ Slack Logic Error: {e}", flush=True)

        # --- 3. URGENT ALERT ---
        if is_urgent and emp_email and N8N_ALERT_URL:
            try:
                alert_payload = {"task_name": name, "owner_name": owner, "email": emp_email}
                requests.post(N8N_ALERT_URL, json=alert_payload, timeout=5)
                calendar_msg += " (🚨 Urgent Email Sent!)"
            except Exception as e:
                print(f"Urgent alert failed: {e}", flush=True)

    return trello_success, calendar_msg

@tool
def create_task_in_trello(task_name: str, description: str = "", owner: str = "Auto"):
    """Creates a single task in Trello. If owner is 'Auto', it will be auto-assigned."""
    if owner == "Auto":
        owner = auto_assign_owner(task_name, description) or get_default_owner()
    success, cal_msg = internal_create_trello(task_name, description, owner)
    if success:
        return f"Success! Created task for {owner}.{cal_msg}"
    return "Failed to create task."

@tool
def send_slack_announcement(message: str):
    """Sends a message to the team Slack channel.
    Use this ONLY for general project announcements.
    🛑 DO NOT use this to confirm meetings.
    🛑 DO NOT use this to confirm task creation.
    🛑 DO NOT use this if the user is rejecting a proposal.
    """
    try:
        requests.post(N8N_SLACK_URL, json={"message": message}, timeout=5)
        return "Success."
    except Exception:
        return "Failed."

# --- 🚀 UPDATED TOOL: Matches 3072 dimensions ---
@tool
def consult_project_memory(query: str, username: str = "placeholder"):
    """Searches project documentation in the vector database."""
    try:
        # 1. Generate Gemini Embedding (Now 3072 dimensions)
        v = generate_embedding(query)
        
        # 2. Query Pinecone
        r = memory_index.query(
            vector=v, 
            top_k=3, 
            include_metadata=True, 
            filter={"username": username} 
        )
        
        if not r['matches']:
            return "No relevant project context found in memory."
            
        return "\n".join([f"- {m['metadata']['text']}" for m in r['matches']])
    except Exception as e:
        return f"Memory Error: {e}"
    
    
@tool
def schedule_meeting_tool(start_time: str, summary: str = "General Meeting", description: str = "No description provided", action: str = "book"):
    """
    Schedules a Google Calendar meeting AND notifies Slack.
    Args:
        start_time: ISO format date string (e.g. "2026-02-01T14:00:00")
        summary: Title of the meeting (Default: "General Meeting")
        description: (Optional) Details
        action: 'check' or 'book'
    """

    if action == "check":
        is_free, msg = check_availability(start_time)
        if is_free:
            return f"Good news! The {start_time} slot is available. Would you like me to book that for you?"
        else:
            # Try to find next slot
            found, next_iso, readable, _ = find_next_free_slot(start_time)
            if found:
                return f"⚠️ BUSY. The requested time is taken. However, {readable} ({next_iso}) is available. Ask the user if they prefer that time."
            return f"⚠️ BUSY. No free slots found nearby."

    result = create_meeting(summary, description, start_time, is_video_call=True, strict_time=True)
    if "Success" in str(result):
        try:
            clean_link = str(result).split(" (Booked")[0].replace("Success! Link: ", "").strip()
            time_part = str(result).split("(Booked at ")[1].replace(")", "")
            slack_msg = f"📅 *NEW MEETING SCHEDULED:*\n📌 *Event:* {summary}\n⏰ *Time:* {time_part}\n📹 *Video Link:* {clean_link}"
            try:
                requests.post(N8N_SLACK_URL, json={"message": slack_msg}, timeout=5)
            except:
                pass
        except:
            pass
    return result

@tool
def execute_project_plan(goal: str, tasks: str | list, budget: float = 0, username: str = "default"):
    """Generates a multi-step plan. Tasks must be a JSON string. Budget is the max limit in dollars."""
    state = get_user_state(username)
    try:
        print(f"🧐 DEBUG RAW AI INPUT: {tasks}")
        print(f"💰 DEBUG BUDGET INPUT: {budget}")
        if isinstance(tasks, str):
            try:
                raw_data = json.loads(tasks)
            except:
                return "Error: Tasks argument was not valid JSON."
        else:
            # It's already a list or dict (LangChain parsed it automatically)
            raw_data = tasks
        
        if isinstance(raw_data, dict) and "tasks" in raw_data:
            raw_data = raw_data["tasks"]
        if not isinstance(raw_data, list):
            return "Error: AI returned invalid JSON structure."

        clean_tasks = []
        total_project_cost = 0

        target_budget = budget

        scheduled_tasks = calculate_smart_timeline(raw_data)

        # Now loop through the SMART list, not the raw list
        for t in scheduled_tasks:
            if isinstance(t, str):
                t = {"name": t, "desc": "Auto-generated task", "owner": "Unassigned"}
            # ensure name exists
            if "name" not in t:
                t["name"] = t.get("task_name") or t.get("title") or t.get("action") or t.get("task") or "Task"
            if "trello card" in t["name"].lower():
                continue
            name = t.get("name")
            desc = t.get("desc") or t.get("description") or ""
            owner = t.get("owner") or t.get("assignee") or "Unassigned"

            if owner == "Unassigned" or not owner:
                owner = auto_assign_owner(name, desc)
            if owner == "Unassigned":
                owner = get_default_owner()
            # --- COST CALCULATION ---
            # A. Time Est
            # --- COST CALCULATION ---
            # Get the duration calculated by the Smart Timeline (default to 2 if missing)
            days = t.get("duration", 2)
            
            # B. Rate Est
            emp_rate = 50
            try:
                if employees_collection:
                    emp_data = employees_collection.find_one({"name": {"$regex": f"^{owner}$", "$options": "i"}})
                    if emp_data: emp_rate = emp_data.get("rate", 50)
            except: pass
            
            # C. Resource/Tool Cost (from AI)
            tool_cost = t.get("tool_cost", 0)
            
            # D. Total
            personnel_cost = days * 8 * emp_rate
            task_total = personnel_cost + tool_cost
            total_project_cost += task_total

            # E. Save to Description
            cost_details = f"💰 **Cost:** ${task_total} (Labor: ${personnel_cost} + Tools: ${tool_cost})"
            timeline_info = ""

            if "start_date" in t:
                timeline_info = f"\n📅 **Timeline:** {t['start_date']} ➝ {t['due_date']}"
            
            desc = f"{desc}\n\n{cost_details}\n⏱ Est: {days} days @ ${emp_rate}/hr"
            
            # ✅ THE FIX: Save the calculated dates into the pending plan
            clean_tasks.append({
                "name": name, 
                "desc": desc, 
                "owner": owner,
                "due_date": t.get("due_date"), 
                "start_date": t.get("start_date")
            })
        # --- RISK ANALYSIS ---
        # Default styling (No budget limit set)
        state['current_budget_warning'] = "" # Reset warning

        # If user set a limit, check it and change the styling
        if target_budget > 0:
            if total_project_cost > target_budget:
                overrun = total_project_cost - target_budget
                
                # 🚨 RED ALERT STYLE
                budget_status_msg = (
                    f"🚨 **Total:** ${total_project_cost}\n"
                    f"⚠️ **Over Budget by:** ${overrun}"
                )
                state['current_budget_warning'] = f"🚨 **BUDGET OVERRUN:** Plan exceeds limit by ${overrun}!"
            
            else:
                remaining = target_budget - total_project_cost
                
                # ✅ GREEN SUCCESS STYLE
                budget_status_msg = (
                    f"✅ **Total:** ${total_project_cost}\n"
                    f"💰 **Under Budget:** ${remaining} remaining"
                )
                state['current_budget_warning'] = "" 
        else:
            # If no budget set, just show total neutral
            budget_status_msg = f"💵 **Total Project Cost:** ${total_project_cost}"
            state['current_budget_warning'] = ""

        # Save this pre-formatted message into the plan
        state['pending_plan'] = {
            "goal": goal, 
            "tasks": clean_tasks, 
            "budget_summary": budget_status_msg 
        }
        
        return "PLAN_STAGED"
    except Exception as e:
        print("❌ PLAN ERROR:", e)
        return f"Error: {e}"

@tool
def check_project_status(dummy: str = "", username: str = "default"):
    """Checks Trello for overdue tasks AND active budget risks."""
    state = get_user_state(username)
    try:
        risks = []
        try:
            print(f"🔍 Fetching cards from: {N8N_GET_ALL_CARDS_URL}")
            response = requests.get(N8N_GET_ALL_CARDS_URL, timeout=5.0)
            
            if response.status_code == 200:
                # 1. Handle Response Type
                
                raw_data = response.json()
                # --- DEBUG PRINT ---
                print(f"📦 Raw Data Type: {type(raw_data)}")
                if isinstance(raw_data, list):
                    print(f"📦 List Length: {len(raw_data)}")
                # -------------------

                # 2. Normalize to List
                cards = []
                if isinstance(raw_data, list):
                    cards = raw_data
                elif isinstance(raw_data, dict):
                    if "data" in raw_data and isinstance(raw_data["data"], list):
                        cards = raw_data["data"]
                    else:
                        cards = [raw_data]
                
                print(f"✅ Received {len(cards)} cards. Checking dates...")

                today = datetime.now().date() # Compare DATES only, ignore time
                
                for c in cards:
                    # Handle n8n wrapper "json": {...}
                    if isinstance(c, dict) and "json" in c: 
                        c = c["json"]
                    
                    if not isinstance(c, dict): continue

                    # Check for 'due' key
                    if c.get("due"):
                        try:
                            # Clean Z and parse
                            due_str = c["due"].replace("Z", "")
                            # Handle standard ISO format
                            d_full = datetime.fromisoformat(due_str)
                            d_date = d_full.date()
                            
                            # LOGIC:
                            # If Due Date is BEFORE Today = Overdue
                            # If Due Date is TODAY = Due Today (Risk)
                            
                            if d_date < today:
                                days_late = (today - d_date).days
                                risk_msg = f"⚠️ OVERDUE ({days_late} days): '{c.get('name', 'Unknown')}'"
                                risks.append(risk_msg)
                                print(f"❌ RISK: {risk_msg}")
                                
                            elif d_date == today:
                                risk_msg = f"⚠️ DUE TODAY: '{c.get('name', 'Unknown')}'"
                                risks.append(risk_msg)
                                print(f"❌ RISK: {risk_msg}")
                                
                        except Exception as e:
                            print(f"⚠️ Error parsing date for '{c.get('name')}': {e}")
                            pass
            else:
                print(f"❌ n8n Error: {response.status_code}")
                return "Error connecting to Trello."

        except Exception as e:
            print(f"⚠️ Trello Fetch Crash: {e}")
            return "Failed to check project status."

        # Add Budget Risks
        if state['current_budget_warning']:
            risks.insert(0, state['current_budget_warning'])

        state['current_risks'] = risks
        
        if not risks:
            return "✅ ALL GOOD. No overdue tasks or budget issues."
        
        return "Risks Found:\n" + "\n".join(risks)
    except Exception as e:
        return f"Error: {e}"
    
@tool
def heal_project_schedule(dummy: str = ""):
    """
    1. Scans Trello (Backlog & Doing).
    2. Phase 1: Moves OVERDUE tasks to the next valid business day.
    3. Phase 2: Moves DEPENDENT tasks to start after their blockers.
    """
    try:
        # Fetch Data
        response = requests.get(N8N_GET_ALL_CARDS_URL)
        raw_data = response.json()

        # --- 🔥 FIX: Normalize Data ---
        cards = []
        if isinstance(raw_data, list):
            cards = raw_data
        elif isinstance(raw_data, dict):
            if "data" in raw_data and isinstance(raw_data["data"], list):
                cards = raw_data["data"]
            else:
                cards = [raw_data]

        task_status = {}
        updates = []
        
        # =========================================================
        # PHASE 1: HEAL ROOT CAUSES (Overdue Tasks)
        # =========================================================
        for c in cards:
            if isinstance(c, dict) and "json" in c: c = c["json"]
            if not isinstance(c, dict): continue

            try:
                if not c.get("due"): continue
                due = datetime.fromisoformat(c["due"].replace("Z", ""))
            except:
                continue 

            effective_due = due

            # Check if overdue OR due today
            if due.date() <= datetime.now().date():
                
                preferred_time = due.time()
                temp_date = datetime.now()
                
                # If time has passed today, start from tomorrow
                if temp_date.time() > preferred_time:
                    temp_date += timedelta(days=1)

                days_added = 0
                while days_added < 1:
                    is_weekend = temp_date.weekday() in WEEKEND_DAYS
                    is_holiday = temp_date.strftime("%Y-%m-%d") in COMPANY_HOLIDAYS
                    if not is_weekend and not is_holiday:
                        days_added += 1
                    else:
                        temp_date += timedelta(days=1)
                
                new_due = datetime.combine(temp_date.date(), preferred_time)

                # Enforce 9-6
                if new_due.hour < 9: new_due = new_due.replace(hour=10, minute=0)
                elif new_due.hour >= 18: new_due = new_due.replace(hour=17, minute=0)

                try:
                    requests.put(
                        f"https://api.trello.com/1/cards/{c['id']}", 
                        params={"key": TRELLO_API_KEY, "token": TRELLO_TOKEN, "due": new_due.isoformat()}
                    )
                    updates.append(f"🔄 Rescheduled Overdue: '{c.get('name')}' to {new_due.strftime('%Y-%m-%d @ %I:%M %p')}")
                    effective_due = new_due 
                except Exception as e:
                    print(f"Failed to update card: {e}")

            task_status[c.get("name")] = effective_due
            if "]" in c.get("name", ""):
                clean_name = c["name"].split("]")[1].strip()
                task_status[clean_name] = effective_due

        # =========================================================
        # PHASE 2: HEAL DEPENDENCIES
        # =========================================================
        for c in cards:
            if isinstance(c, dict) and "json" in c: c = c["json"]
            if not isinstance(c, dict): continue
            
            desc = c.get("desc", "")
            if desc and "Blocked By:" in desc:
                try:
                    blocker_part = desc.split("Blocked By:")[1]
                    blocker_clean = blocker_part.replace("*", "")
                    blocker_line = blocker_clean.split("\n")[0].strip()
                    
                    # Handle multiple blockers (comma separated)
                    raw_blockers = [b.strip() for b in blocker_line.split(",")]
                    
                    max_blocker_end = None
                    active_blocker_name = ""

                    for b in raw_blockers:
                        if "]" in b: b = b.split("]")[1].strip()
                        if b in task_status:
                            b_end = task_status[b]
                            if max_blocker_end is None or b_end > max_blocker_end:
                                max_blocker_end = b_end
                                active_blocker_name = b
                    
                    if max_blocker_end:
                        blocker_end = max_blocker_end
                        
                        my_current_due = None
                        if c.get("due"):
                            my_current_due = datetime.fromisoformat(c["due"].replace("Z", ""))
                        
                        if my_current_due and my_current_due <= blocker_end:
                            
                            pref_time = my_current_due.time()
                            temp_date = blocker_end
                            days_added = 0
                            while days_added < 1:
                                temp_date += timedelta(days=1)
                                is_weekend = temp_date.weekday() in WEEKEND_DAYS
                                is_holiday = temp_date.strftime("%Y-%m-%d") in COMPANY_HOLIDAYS
                                if not is_weekend and not is_holiday:
                                    days_added += 1
                                else:
                                    temp_date += timedelta(days=1)
                            
                            new_due = datetime.combine(temp_date.date(), pref_time)

                            if new_due.hour < 9: new_due = new_due.replace(hour=10, minute=0)
                            elif new_due.hour >= 18: new_due = new_due.replace(hour=17, minute=0)

                            requests.put(
                                f"https://api.trello.com/1/cards/{c['id']}", 
                                params={"key": TRELLO_API_KEY, "token": TRELLO_TOKEN, "due": new_due.isoformat()}
                            )
                            updates.append(f"🛠️ Pushed Dependent: '{c.get('name')}' to {new_due.strftime('%Y-%m-%d @ %I:%M %p')} (Blocked by {active_blocker_name})")
                            
                            # Update status for chains
                            effective_due = new_due
                            task_status[c.get("name")] = effective_due
                            if "]" in c.get("name", ""):
                                clean_name = c["name"].split("]")[1].strip()
                                task_status[clean_name] = effective_due

                except Exception as e:
                    print(f"Dependency check error: {e}")
                    continue
        
        return "\n".join(updates) if updates else "Schedule Healthy (No conflicts found)."
    except Exception as e:
        return f"Error healing: {e}"
    


@tool
def check_team_workload(dummy: str = ""):
    """Checks the current workload of each team member by counting their active Trello cards.
    Returns a summary of who is available, busy, or overloaded."""
    try:
        # 1. Fetch all cards from Trello
        response = requests.get(N8N_GET_ALL_CARDS_URL, timeout=15)
        if response.status_code != 200:
            return "Failed to fetch Trello data."
        
        raw_data = response.json()
        cards = []
        if isinstance(raw_data, list):
            cards = raw_data
        elif isinstance(raw_data, dict) and "data" in raw_data:
            cards = raw_data["data"]
        
        # 2. Count active cards per owner
        owner_counts = {}
        trello_done_list = os.getenv("TRELLO_DONE_LIST_ID", "6922b7e358b2e5d625ad65ba")
        
        for c in cards:
            if isinstance(c, dict) and "json" in c:
                c = c["json"]
            if not isinstance(c, dict):
                continue
            
            # Skip completed cards
            if c.get("idList") == trello_done_list or c.get("dueComplete") is True:
                continue
            
            # Extract owner from [Owner] prefix in card name
            card_name = c.get("name", "")
            if "[" in card_name and "]" in card_name:
                owner = card_name.split("]")[0].replace("[", "").strip()
                owner_counts[owner] = owner_counts.get(owner, 0) + 1
        
        # 3. Cross-reference with employee roster
        employees = list(employees_collection.find({}, {"_id": 0, "name": 1, "role": 1}))
        
        result_lines = []
        for emp in employees:
            name = emp.get("name", "Unknown")
            role = emp.get("role", "")
            count = owner_counts.get(name, 0)
            
            if count >= 6:
                status = "🔴 OVERLOADED"
            elif count >= 3:
                status = "🟡 BUSY"
            else:
                status = "🟢 AVAILABLE"
            
            result_lines.append(f"{name} ({role}): {count} active tasks — {status}")
        
        if not result_lines:
            return "No team members found in the roster."
        
        return "📊 **Team Workload Report:**\n" + "\n".join(result_lines)
    except Exception as e:
        return f"Error checking workload: {e}"


@tool
def log_time(task_name: str, hours: float, note: str = ""):
    """Logs time spent on a task. Use when a team member reports hours worked.
    Args:
        task_name: The name of the task worked on
        hours: Number of hours spent
        note: Optional description of work done
    """
    try:
        entry = {
            "task_name": task_name,
            "logged_by": "via_chat",
            "hours": hours,
            "note": note,
            "timestamp": datetime.now()
        }
        time_logs_collection.insert_one(entry)
        return f"✅ Logged {hours}h on \"{task_name}\". {('Note: ' + note) if note else ''}"
    except Exception as e:
        return f"Error logging time: {e}"


@tool
def send_deadline_alerts(days_ahead: int = 2):
    """Scans Trello for tasks due within N days and sends a Slack alert summary.
    Use when user asks to "check deadlines", "any urgent tasks?", or "what's due soon".
    Args:
        days_ahead: Number of days ahead to check (default: 2)
    """
    try:
        response = requests.get(N8N_GET_ALL_CARDS_URL, timeout=15)
        if response.status_code != 200:
            return "Failed to fetch Trello cards."

        raw_data = response.json()
        cards = raw_data if isinstance(raw_data, list) else raw_data.get("data", [])

        today = datetime.now().date()
        cutoff = today + timedelta(days=days_ahead)
        trello_done_list = os.getenv("TRELLO_DONE_LIST_ID", "")

        urgent_tasks = []
        overdue_tasks = []

        for c in cards:
            if isinstance(c, dict) and "json" in c:
                c = c["json"]
            if not isinstance(c, dict):
                continue
            if c.get("idList") == trello_done_list or c.get("dueComplete"):
                continue

            due_raw = c.get("due")
            if not due_raw:
                continue

            try:
                due_date = datetime.fromisoformat(due_raw.replace("Z", "+00:00")).date()
            except:
                continue

            name = c.get("name", "Unnamed task")
            if due_date < today:
                overdue_tasks.append(f"🔴 *[OVERDUE]* {name} (was due {due_date})")
            elif due_date <= cutoff:
                urgent_tasks.append(f"🟡 *[DUE SOON]* {name} (due {due_date})")

        if not urgent_tasks and not overdue_tasks:
            return f"✅ No tasks overdue or due in the next {days_ahead} days. Team is on track!"

        all_alerts = overdue_tasks + urgent_tasks
        message = f"⏰ *Deadline Alert — Next {days_ahead} Days*\n" + "\n".join(all_alerts)

        # Send to Slack
        try:
            requests.post(N8N_SLACK_URL, json={"message": message}, timeout=10)
        except:
            pass

        return message

    except Exception as e:
        return f"Error checking deadlines: {e}"

@tool
def auto_plan_sprint(sprint_name: str, duration_weeks: int = 2, focus_area: str = "", username: str = "default"):
    """
    Intelligently reads the project backlog and plans a new sprint based on team capacity.
    Provides an optional focus_area (e.g. 'checkout', 'security') to prioritize related tasks.
    """
    try:
        # 1. Calculate Capacity
        devs = list(employees_collection.find())
        # Assume 6 productive hours / day / dev. 5 days a week.
        sprint_days = duration_weeks * 5
        capacity_hours = len(devs) * sprint_days * 6
        
        # 2. Get Backlog Tasks (not in any sprint, not done)
        query = {"sprint_id": {"$in": [None, ""]}, "status": {"$ne": "done"}}
        tasks = list(tasks_collection.find(query))
        
        if not tasks:
            return "No tasks in the backlog to plan."
            
        def score_task(t):
            score = 0
            text = (t.get("name","") + " " + t.get("description","")).lower()
            if focus_area and focus_area.lower() in text:
                score += 100
            return score
            
        tasks.sort(key=score_task, reverse=True)
        
        # 3. Create Sprint
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_weeks * 7)
        
        sprint_doc = {
            "name": sprint_name,
            "goal": f"Focus: {focus_area}" if focus_area else "General Backlog",
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "capacity_hours": capacity_hours,
            "project_id": "default",
            "status": "planning",
            "created_by": username,
            "created_at": datetime.now()
        }
        result = sprints_collection.insert_one(sprint_doc)
        sprint_id = str(result.inserted_id)
        
        # 4. Fill Sprint to capacity
        assigned_hours = 0
        assigned_tasks = []
        for t in tasks:
            est = t.get("estimated_hours", 0)
            if est == 0: est = 4 # default to 4 hours if not estimated
            
            if assigned_hours + est <= capacity_hours:
                assigned_hours += est
                tasks_collection.update_one({"_id": t["_id"]}, {"$set": {"sprint_id": sprint_id}})
                assigned_tasks.append(t.get("name"))
                
        return f"Sprint '{sprint_name}' created successfully! Capacity: {capacity_hours}h. Assigned {len(assigned_tasks)} tasks ({assigned_hours}h estimated). Tasks assigned: {', '.join(assigned_tasks)}"
    except Exception as e:
        return f"Error planning sprint: {e}"

# Bind tools
llm_with_tools = llm.bind_tools([create_task_in_trello, send_slack_announcement, consult_project_memory, execute_project_plan, check_project_status, schedule_meeting_tool, heal_project_schedule, check_team_workload, log_time, send_deadline_alerts, auto_plan_sprint])
# ==========================================
# 🧠 MEMORY & PERSISTENCE LAYER
# ==========================================

# --------------------
# ENDPOINTS
# --------------------

@app.post("/user/profile")
async def update_profile(profile: ProfileUpdate, username: str = Depends(get_current_user)):
    try:
        users_collection.update_one(
            {"username": username},
            {"$set": {"display_name": profile.display_name, "email": profile.email}}
        )
        return {"msg": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/profile")
async def get_profile(username: str = Depends(get_current_user)):
    user = users_collection.find_one({"username": username}, {"_id": 0, "password": 0})
    return user or {"display_name": "Project Manager", "email": ""}

def save_chat_message(session_id: str,role: str, content: str):
    """Saves a message to MongoDB."""
    try:
        msg = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        }
        chats_collection.insert_one(msg)
    except Exception as e:
        print(f"Error saving chat: {e}")

def get_chat_history(session_id: str,limit=5):
    """Loads context from DB + System Prompt."""
    # Start with System Prompt (We reconstruct it to ensure it's fresh)
    messages = [SystemMessage(content=chat_history[0].content)] if chat_history else []
    
    try:
        # Filter MongoDB by "session_id"
        recent_chats = list(chats_collection.find(
            {"session_id": session_id} # <--- Filter applied here
        ).sort("timestamp", -1).limit(limit))
        
        # Reverse to put in chronological order (Oldest -> Newest)
        for chat in reversed(recent_chats):
            if chat["role"] == "user":
                messages.append(HumanMessage(content=chat["content"]))
            else:
                # Treat AI responses as messages
                messages.append(AIMessage(content=f"{chat['content']}"))
    except Exception:
        pass
        
    return messages

# --- 🛠️ UNIFIED TOOL PROCESSOR (The "Brain" Logic) ---
def process_tool_calls(response, context_messages,username):
    """
    Handles tool calls recursively. 
    Used by both /chat and /upload to ensure consistent behavior.
    """
    
    final_text = response.content
    approval_required = False
    
    # Track executed tools to prevent infinite loops
    executed_tools = set()
    
    # We might need to loop if the AI reads memory -> then decides to plan
    current_response = response
    
    # Loop while the AI wants to call tools (Max 3 turns for safety)
    for _ in range(3): 
        if not current_response.tool_calls:
            break
        
        # ✅ CRITICAL FIX: Add the AI's "Tool Call" message to history
        context_messages.append(current_response)
            
        for tc in current_response.tool_calls:
            fn = tc["name"]
            args = tc["args"]
            
            # Deduplication
            if fn in executed_tools and fn != "consult_project_memory": 
                continue
            executed_tools.add(fn)
            
            tool_result = "Tool executed."

            # --- A. PLANNING ---
            if fn == "execute_project_plan":
                args['username'] = username
                res = execute_project_plan.invoke(args)
                if res == "PLAN_STAGED":
                    approval_required = True
                    if get_user_state(username)['pending_plan']:
                        pending_plan = get_user_state(username)['pending_plan']
                        preview = "\n".join([f"• {t.get('name')} → {t.get('owner')}" for t in pending_plan["tasks"]])
                        budget = pending_plan.get("budget_summary", "")
                        final_text = f"I have drafted a plan based on the request:\n{budget}\n\n{preview}\n\nProceed?"
                        return final_text, approval_required # Stop here, wait for human
                else:
                    tool_result = str(res)

            # --- B. STANDARD TOOLS ---
            elif fn == "create_task_in_trello":
                tool_result = create_task_in_trello.invoke(args)
            elif fn == "send_slack_announcement":
                send_slack_announcement.invoke(args)
                tool_result = "Message sent."
            elif fn == "check_project_status":
                args['username'] = username
                tool_result = check_project_status.invoke(args)
            elif fn == "schedule_meeting_tool":
                tool_result = schedule_meeting_tool.invoke(args)
                # ✅ FIX: Only return immediately if it was a BOOKING (Success/Error).
                # If it was a CHECK (Available/Busy), let the loop continue so AI can ask the user.
                if "✅ Available" in str(tool_result) or "⚠️ BUSY" in str(tool_result):
                    pass 
                else:
                    return str(tool_result), approval_required
            elif fn == "heal_project_schedule":
                tool_result = heal_project_schedule.invoke(args)
            elif fn == "check_team_workload":
                tool_result = check_team_workload.invoke(args)
            elif fn == "log_time":
                tool_result = log_time.invoke(args)
            elif fn == "send_deadline_alerts":
                tool_result = send_deadline_alerts.invoke(args)
            if fn == "consult_project_memory":
                # ✅ INJECT USERNAME (AI doesn't provide this, we do)
                args["username"] = username 
                tool_result = consult_project_memory.invoke(args)
                tool_result = f"Memory Findings: {tool_result}"

            # Append result to context so AI knows what happened
            context_messages.append(HumanMessage(content=str(tool_result)))
            
            # Update final text fallback
            # ✅ FIX: Do not show raw memory logs to the user. 
            # Only update final_text if it's NOT a memory search.
            if fn not in ["consult_project_memory", "check_project_status"]:
                final_text = str(tool_result)
        # Ask AI again with the tool outputs
        current_response = llm_with_tools.invoke(context_messages)
        if current_response.content:
            final_text = current_response.content
            
    return final_text, approval_required

@app.post("/upload")
async def upload_document(file: UploadFile = File(...), username: str = Depends(get_current_user)):
    """
    Autonomous Trigger: Uploads doc, embeds it, and forces AI to analyze it.
    TAGS the data with the current username so others can't see it.
    """
    try:
        # 1. Read File
        content = await file.read()
        text = content.decode("utf-8")
        
        # 2. Embed into Pinecone
        chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
        vectors = []
        for i, chunk in enumerate(chunks):
            embedding = generate_embedding(chunk)
            vectors.append({
                "id": f"{username}_{file.filename}_part_{i}", 
                "values": embedding,
                "metadata": {"text": chunk, "source": file.filename, "username": username}
            })
        
        memory_index.upsert(vectors=vectors)
        
        # 3. AUTONOMOUS TRIGGER
        system_trigger = f"""
        SYSTEM_EVENT: User uploaded '{file.filename}'. 
        Action Required:
        1. Read the document content from memory to understand the context.
        2. Do NOT output the raw content.
        3. Do NOT generate a plan yet.
        4. Simply reply: "✅ I have processed {file.filename} and stored it in memory. I am ready to use this context when you ask."
        """
        
        # Save User's System Trigger
        save_chat_message("system_upload", "user", system_trigger)
        
        # 4. INVOKE & EXECUTE
        messages = [HumanMessage(content=system_trigger)]
        response = llm_with_tools.invoke(messages)
        
        final_reply, approval_required = process_tool_calls(response, messages, username)
        
        # ✅ ADD THIS LINE BACK (Saves the AI's reply to history)
        save_chat_message("system_upload", "ai", str(final_reply))
        
        return {"status": "processed", "reply": final_reply, "approval_required": approval_required}

    except Exception as e:
        print(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        if users_collection is None or db is None:
            raise HTTPException(status_code=500, detail="Database connection failed.")
        db.command("ping")
        if not SECRET_KEY or SECRET_KEY == "default_secret":
            raise HTTPException(status_code=500, detail="Server configuration error: SECRET_KEY not set")
        user = users_collection.find_one({"username": form_data.username})
        if not user or not pwd_context.verify(form_data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        user_role = user.get("role", "developer")
        token = jwt.encode({"sub": user["username"], "role": user_role}, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer", "role": user_role}
    except HTTPException:
        raise
    except Exception as e:
        print("Login error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register")
async def register(user: User):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Exists")
    # First user auto-becomes admin
    total_users = users_collection.count_documents({})
    role = "admin" if total_users == 0 else user.role
    if role not in VALID_ROLES:
        role = "developer"
    users_collection.insert_one({
        "username": user.username,
        "password": pwd_context.hash(user.password),
        "role": role
    })
    return {"msg": f"Created with role: {role}"}

@app.post("/employees")
def add_employee(emp: Employee, user_info: dict = Depends(require_role("admin", "pm"))):
    try:
        if not emp.trello_id and emp.email:
            emp.trello_id = get_trello_id_by_email(emp.email)
        employees_collection.insert_one(emp.dict())
        refresh_system_prompt()
        return {"msg": f"Added {emp.name} (ID: {emp.trello_id})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/employees")
def get_employees(username: str = Depends(get_current_user)):
    return list(employees_collection.find({}, {"_id": 0}))

@app.post("/chat")
def chat_endpoint(req: UserRequest, username: str = Depends(get_current_user)):
    # 1. Save User Message
    save_chat_message(req.session_id, "user", req.message)
    
    # 2. Load History
    context_messages = get_chat_history(req.session_id, limit=5)
    
    # 3. Invoke AI
    response = llm_with_tools.invoke(context_messages)
    
    # 4. Process Tools (✅ PASS USERNAME HERE)
    final_text, approval_required = process_tool_calls(response, context_messages, username)
    
    # 5. Save AI Reply
    save_chat_message(req.session_id, "ai", str(final_text))
    
    return {"reply": final_text, "approval_required": approval_required}

@app.get("/chat/history/{session_id}")
def get_full_history(session_id: str, username: str = Depends(get_current_user)):
    """Returns the full chat history for the UI."""
    try:
        # Fetch all messages for this session, sorted oldest to newest
        history = list(chats_collection.find(
            {"session_id": session_id}, 
            {"_id": 0, "role": 1, "content": 1, "timestamp": 1}
        ).sort("timestamp", 1))
        return history
    except Exception as e:
        return {"error": str(e)}

@app.post("/approve")
def approve_plan(req: ApproveRequest, user_info: dict = Depends(require_role("admin", "pm"))):
    username = user_info["username"]
    pending_plan = get_user_state(username)['pending_plan']
    if not pending_plan:
        return {"status": "No plan."}
    results = []
    current_hour = 9
    for t in pending_plan["tasks"]:
        name = t.get("name", "Task")
        owner = t.get("owner", "Unassigned")
        desc = t.get("desc", "")
        smart_date = t.get("due_date")
        success, cal_msg = internal_create_trello(
            name, desc, owner, 
            start_hour=current_hour, 
            specific_due_date=smart_date 
        )
        status_text = f"Created: {name}"
        if cal_msg:
            status_text += " (+Calendar)"
        results.append(status_text)
        current_hour += 2
        if current_hour > 18:
            current_hour = 9
        print(f"⏳ Waiting 5s for n8n to finish processing '{name}'...", flush=True)
        time_module.sleep(5)
    # 1️⃣ DASHBOARD MESSAGE (Keep this exactly as is so your charts don't break)
    budget_info = pending_plan.get("budget_summary", "No Budget Info")
    dashboard_msg = (
        f"✅ *APPROVED:* {pending_plan['goal']}\n"
        f"{budget_info}\n"
        f"----------------------------------\n"
        f"{chr(10).join(results)}"
    )
    # 2️⃣ PROFESSIONAL UI MESSAGE (For the user chat history)
    activation_msg = (
        f"🚀 **Project Execution Plan Activated!**\n\n"
        f"✅ **Goal:** {pending_plan['goal']}\n"
        f"{budget_info}\n"
        f"----------------------------------\n"
        f"The team has been notified via Slack and Trello cards have been synced to Google Calendars."
    )

    try:
        save_chat_message("system_plan_management", "ai", dashboard_msg)
        
        # Save the professional message to the user's ACTUAL session (for refresh persistence)
        save_chat_message(req.session_id, "ai", activation_msg)
        
        # 2. Send to Slack
        requests.post(N8N_SLACK_URL, json={"message": dashboard_msg}, timeout=5)
    except Exception as e:
        print(f"❌ Error during save: {e}")

    get_user_state(username)['pending_plan'] = None
    return {"reply": activation_msg}
# 🔐 RBAC: Only PM/Admin can modify employees
@app.put("/employees/{email}")
def update_employee(email: str, emp: Employee, user_info: dict = Depends(require_role("admin", "pm"))):
    employees_collection.update_one({"email": email}, {"$set": emp.dict()})
    return {"msg": "Updated successfully"}

@app.delete("/employees/{email}")
def delete_employee(email: str, user_info: dict = Depends(require_role("admin", "pm"))):
    employees_collection.delete_one({"email": email})
    return {"msg": "Deleted successfully"}

@app.post("/reject")
def reject_plan(req: RejectRequest): # 🚀 No longer Optional; we need that session_id
    global pending_plan, current_budget_warning
    
    # 1. Capture the goal for the message before we delete it
    proj_name = pending_plan.get("goal", "the proposed plan") if pending_plan else "the plan"
    
    # 2. Clear the internal memory
    pending_plan = None
    state['current_budget_warning'] = "" 
    
    # 3. Create a Professional Message
    reject_msg = f"❌ **Plan Rejected:** The execution strategy for '{proj_name}' has been cancelled.\n**Reason:** {req.reason}"
    
    # 4. ✅ SAVE TO DB: This ensures it shows up permanently after a refresh
    save_chat_message(req.session_id, "ai", reject_msg)


    # 6. Force refresh project status to clear the dashboard warning
    check_project_status.invoke({"dummy": "refresh", "username": username})
    
    # 7. Return to frontend for instant UI update
    return {"reply": reject_msg}

@app.get("/risks")
def get_risks(username: str = Depends(get_current_user)):
    """
    Force a refresh of the project status immediately 
    so the Frontend gets live data on load.
    """
    # 1. Run the check logic explicitly!
    # This updates the 'current_risks' global variable
    check_project_status.invoke({"dummy": "refresh", "username": username})
    
    # 2. Return the freshly updated list
    return {"risks": get_user_state(username)['current_risks']}


# ==========================================
# 🚀 NEW DASHBOARD ENDPOINT
# ==========================================

@app.get("/dashboard/data", response_model=DashboardStats)
def get_dashboard_data(username: str = Depends(get_current_user)):
    real_active_agents = get_active_workflow_count()
    
    # 1. INITIALIZE EVERYTHING
    tasks_due_today = 0
    overdue_tasks = 0
    status_counts = {"Completed": 0, "In Progress": 0, "Not Started": 0}
    total_employees = 0
    if employees_collection is not None:
        total_employees = employees_collection.count_documents({})
    
    today = datetime.now().date()
    completed_line = {(today + timedelta(days=i)).strftime("%d %b"): 0 for i in range(-2, 12)}
    active_line = {(today + timedelta(days=i)).strftime("%d %b"): 0 for i in range(-2, 12)}
    upcoming_line = {(today + timedelta(days=i)).strftime("%d %b"): 0 for i in range(-2, 12)}
    sorted_dates = list(completed_line.keys())

    # --- 🚀 STEP A: DYNAMIC SIDEBAR & BUDGET FROM MONGODB ---
    # Fetch last 3 approvals to fill sidebar and get current project totals
    # --- 🚀 STEP A: DYNAMIC SIDEBAR & BUDGET FROM MONGODB ---
    # --- 🚀 STEP A: DYNAMIC SIDEBAR & BUDGET FROM MONGODB ---
    import re

    approved_chats = list(chats_collection.find(
        {"content": {"$regex": "APPROVED:"}}, 
        {"content": 1, "_id": 0}
    ).sort("timestamp", -1).limit(3))

    sidebar_projects = []
    total_project_budget = "$0"
    current_project_name = "Core Operations"

    for i, msg in enumerate(approved_chats):
        content = msg["content"]
        try:
            # 1. Capture text after APPROVED: up until the first newline or emoji
            # The [^\n\r🚨💰✅💵*]+ part ensures we don't grab icons or markdown stars
            name_match = re.search(r"APPROVED:?\*?\*?\s*([^\n\r🚨💰✅💵*]+)", content)
            
            if name_match:
                # 👈 THE FIX: Explicitly remove literal "\n" strings and extra stars
                proj_name = name_match.group(1).replace("\\n", "").replace("*", "").strip()
                
                if proj_name and proj_name not in sidebar_projects:
                    sidebar_projects.append(proj_name)
                
                # Use the most recent one for main header
                if i == 0:
                    current_project_name = proj_name
                    # Find dollar amount line
                    budget_match = re.search(r"Total:?\*?\*?\s*(\$[\d,.]+)", content)
                    if budget_match:
                        total_project_budget = budget_match.group(1).strip()
        except Exception as e:
            print(f"⚠️ Parsing error: {e}")

    if not sidebar_projects:
        sidebar_projects = ["Nexus Platform", "Agent Core", "Sync Engine"]
    
    sidebar_projects = sidebar_projects[:3]
    
    # --- 🚀 STEP B: TRELLO DATA PROCESSING ---
    try:
        analytics_url = os.getenv("N8N_DASHBOARD_URL") or N8N_GET_ALL_CARDS_URL
        response = requests.get(analytics_url, timeout=30)
        
        # 1. Initialize storage for Analysis
        finance_items = [] 
        total_committed_dollars = 0
        
        if response.status_code == 200:
            raw_data = response.json()
            
            # Handle unboxing logic correctly
            if isinstance(raw_data, list) and len(raw_data) > 0:
                first_item = raw_data[0]
                cards = first_item.get("", raw_data) if isinstance(first_item, dict) else raw_data
            else:
                cards = raw_data

            # Define today at the start of the processing block
            # Define today at the start of the processing block
            today_dt = datetime.now().date()

            for c in cards:
                if isinstance(c, dict) and "json" in c: c = c["json"]
                if not isinstance(c, dict): continue

                # --- 1. STATUS & CHART LOGIC ---
                list_id = c.get("idList")
                trello_done_list = os.getenv("TRELLO_DONE_LIST_ID", "6922b7e358b2e5d625ad65ba")
                trello_in_progress_list = os.getenv("TRELLO_IN_PROGRESS_LIST_ID", "6922b7e358b2e5d625ad65b9")
                
                is_done = (list_id == trello_done_list) or c.get("dueComplete") is True

                if is_done:
                    status_counts["Completed"] += 1
                elif list_id == trello_in_progress_list:
                    status_counts["In Progress"] += 1
                else:
                    status_counts["Not Started"] += 1
                
                # --- 🚨 CHART & COUNTER LOGIC (THE FIX) ---
                if c.get("due"):
                    try:
                        # Standardize date parsing
                        due_dt_full = datetime.fromisoformat(c["due"].replace("Z", "+00:00"))
                        due_dt = due_dt_full.date()
                        date_str = due_dt.strftime("%d %b") # Format to match your sorted_dates keys

                        # A. Update Line Chart Dictionaries if the date exists in our range
                        if date_str in completed_line:
                            if is_done:
                                completed_line[date_str] += 1
                            elif list_id == trello_in_progress_list:
                                active_line[date_str] += 1
                            else:
                                upcoming_line[date_str] += 1

                        # B. Update Dashboard Top Counters
                        if not is_done:
                            if due_dt < today_dt:
                                overdue_tasks += 1
                            elif due_dt == today_dt:
                                tasks_due_today += 1
                    except Exception as e:
                        print(f"Date parse error: {e}")

                # --- 2. FINANCIAL BURN ANALYSIS ---
                desc = c.get("desc", "")
                if "💰 **Cost:**" in desc:
                    try:
                        raw_amt = desc.split("💰 **Cost:**")[1].split("(")[0].replace("$", "").replace(",", "").strip()
                        cost_val = int(float(raw_amt))
                        total_committed_dollars += cost_val 

                        if cost_val >= 500:
                            finance_items.append({
                                "date": datetime.now().strftime("%b %d"),
                                "category": "Major Resource",
                                "details": c.get("name").split("]")[-1].strip(),
                                "amount": f"${cost_val}",
                                "status": "Released" if is_done else "Allocated",
                                "isPositive": False,
                                "numeric": cost_val 
                            })
                    except: pass

            # 2. PM ANALYSIS: Sort by highest risk (highest cost)
            finance_items.sort(key=lambda x: x.get('numeric', 0), reverse=True)

            # --- BUDGET BURN GAUGE ---
            burn_percentage = 0
            try:
                budget_str = total_budget_str if 'total_budget_str' in dir() else "0"
                # Parse numeric from strings like "$45,000" or "45000"
                budget_nums = [float(x.replace(",","").replace("$","").replace("-","")) 
                               for x in [budget_str] if any(c.isdigit() for c in x)]
                if budget_nums:
                    total_b = budget_nums[0]
                    # Spent = sum of negative finance items
                    spent = sum(
                        float(fi.get("amount","0").replace("$","").replace(",","").replace("-",""))
                        for fi in finance_items if not fi.get("isPositive", True)
                    )
                    burn_percentage = min(round((spent / total_b * 100), 1) if total_b > 0 else 0, 100)
            except Exception as be:
                print(f"Burn gauge error: {be}")

            # --- BURNDOWN CHART DATA ---
            burndown_data = {"labels": [], "planned": [], "actual": []}
            try:
                today_bd = datetime.now().date()
                # Build a 14-day burndown: total tasks minus done per day
                total_bd_tasks = len(cards)
                done_cards = [c for c in cards
                              if (c.get("json", c) if isinstance(c, dict) else c).get("dueComplete")]
                
                burndown_labels = []
                planned_line = []
                actual_line = []
                
                for i in range(14, -1, -1):
                    day = today_bd - timedelta(days=i)
                    burndown_labels.append(day.strftime("%b %d"))
                    # Planned: linear burn from total to 0
                    planned_line.append(max(0, total_bd_tasks - round((14 - i) * total_bd_tasks / 14)))
                    # Actual: remaining tasks (simplified)
                    done_by_day = sum(1 for c in done_cards if True)  # simplified
                    actual_remaining = max(0, total_bd_tasks - round(len(done_cards) * (14 - i) / 14))
                    actual_line.append(actual_remaining)
                
                burndown_data = {
                    "labels": burndown_labels,
                    "planned": planned_line,
                    "actual": actual_line
                }
            except Exception as bde:
                print(f"Burndown calc error: {bde}")

            # --- TEAM WORKLOAD CALCULATION ---
            workload_items = []
            try:
                all_employees = list(employees_collection.find({}, {"_id": 0, "name": 1, "role": 1}))
                owner_card_counts = {}
                trello_done_id = os.getenv("TRELLO_DONE_LIST_ID", "6922b7e358b2e5d625ad65ba")
                for c in cards:
                    card_data = c
                    if isinstance(card_data, dict) and "json" in card_data: card_data = card_data["json"]
                    if not isinstance(card_data, dict): continue
                    if card_data.get("idList") == trello_done_id or card_data.get("dueComplete"): continue
                    cn = card_data.get("name", "")
                    if "[" in cn and "]" in cn:
                        ow = cn.split("]")[0].replace("[", "").strip()
                        owner_card_counts[ow] = owner_card_counts.get(ow, 0) + 1
                
                for emp in all_employees:
                    emp_name = emp.get("name", "Unknown")
                    emp_role = emp.get("role", "")
                    count = owner_card_counts.get(emp_name, 0)
                    if count >= 6:
                        wl_status = "overloaded"
                    elif count >= 3:
                        wl_status = "busy"
                    else:
                        wl_status = "available"
                    workload_items.append({"name": emp_name, "role": emp_role, "active_tasks": count, "status": wl_status})
            except Exception as e:
                print(f"Workload calc error: {e}")

            # --- TIME TRACKING & NATIVE PROJECT TASKS: Estimated vs Actual ---
            try:
                # Add native tasks to finance_items
                native_tasks = list(tasks_collection.find({}, {"_id": 0}))
                for t in native_tasks:
                    est = t.get("estimated_hours", 0)
                    act = t.get("actual_hours", 0)
                    
                    # If actual_hours is not directly on the task, sum from time_logs
                    if act == 0 and time_logs_collection:
                        logs = list(time_logs_collection.find({"task_name": t.get("name")}))
                        act = sum(l.get("hours", 0) for l in logs)
                        
                    # Calculate cost (assuming $50/hr average blend)
                    est_cost = est * 50
                    act_cost = act * 50
                    
                    # We add this as a finance item
                    if est > 0 or act > 0:
                        status = "✅ Under Budget" if act <= est else "⚠️ Over Budget"
                        finance_items.append({
                            "date": t.get("due_date", datetime.now().strftime("%b %d")),
                            "category": "Native Task",
                            "details": t.get("name", "Unknown Task"),
                            "amount": f"${act_cost:,.0f} / ${est_cost:,.0f}",
                            "status": status,
                            "isPositive": act <= est,
                            "numeric": act_cost,
                            "estimated_hours": est,
                            "actual_hours": act
                        })
            except Exception as e:
                print(f"Native task finance calc error: {e}")

            # 🚀 FIND THE USER RECORD USING THE AUTHENTICATED USERNAME
            user_record = users_collection.find_one({"username": username}, {"display_name": 1, "role": 1})
            
            # 🚀 FALLBACK: If they haven't set a name yet, use "Project Manager"
            display_name = user_record.get("display_name", "Project Manager") if user_record else "Project Manager"
            user_role = user_record.get("role", "developer") if user_record else "developer"
            return {
                "tasks_due": tasks_due_today,
                "overdue": overdue_tasks,
                "active": real_active_agents,
                "resolved_risks": status_counts["Completed"],
                "in_progress": status_counts["In Progress"], 
                "not_started": status_counts["Not Started"], 
                "total_team": total_employees,
                "total_budget": total_project_budget,
                "user_display_name": display_name,
                "committed_budget": f"${total_committed_dollars}", # Total board reality
                "current_project": current_project_name,
                "recent_projects": sidebar_projects,
                "line_chart": {
                    "labels": sorted_dates,
                    "datasets": [
                        {"label": "Completed", "data": [completed_line[d] for d in sorted_dates], "borderColor": "#6C5DD3", "backgroundColor": ["transparent"], "tension": 0.4},
                        {"label": "Active", "data": [active_line[d] for d in sorted_dates], "borderColor": "#FFCE73", "backgroundColor": ["transparent"], "tension": 0.4},
                        {"label": "Upcoming", "data": [upcoming_line[d] for d in sorted_dates], "borderColor": "#3F8CFF", "backgroundColor": ["transparent"], "tension": 0.4}
                    ]
                },
                "donut_chart": {
                    "labels": ["Completed", "In Progress", "Not Started"],
                    "datasets": [{
                        "label": "Tasks",
                        "data": [status_counts["Completed"], status_counts["In Progress"], status_counts["Not Started"]],
                        "backgroundColor": ["#6C5DD3", "#3F8CFF", "#FFCE73"]
                    }]
                },
                "finance_table": finance_items[:5], # Top 5 High-Impact items
                "team_workload": workload_items,
                "burn_percentage": burn_percentage,
                "burndown_chart": burndown_data,
                "user_role": user_role
            }

    except Exception as e:
        print(f"⚠️ Dashboard Analytics Error: {e}")
        return {}
    

# ==========================================
# ⏱ TIME TRACKING ENDPOINTS
# ==========================================

@app.post("/time-log")
def create_time_log(log: TimeLogRequest, username: str = Depends(get_current_user)):
    """Log hours spent on a task."""
    try:
        entry = {
            "task_name": log.task_name,
            "logged_by": username,
            "hours": log.hours,
            "note": log.note,
            "timestamp": datetime.now()
        }
        time_logs_collection.insert_one(entry)
        return {"msg": f"Logged {log.hours}h on '{log.task_name}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/time-log/{task_name}")
def get_time_logs(task_name: str, username: str = Depends(get_current_user)):
    """Get all time entries for a specific task."""
    try:
        logs = list(time_logs_collection.find(
            {"task_name": {"$regex": task_name, "$options": "i"}},
            {"_id": 0}
        ).sort("timestamp", -1))
        total_hours = sum(l.get("hours", 0) for l in logs)
        return {"task_name": task_name, "total_hours": total_hours, "entries": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 📁 MULTI-PROJECT ENDPOINTS
# ==========================================

@app.post("/projects")
def create_project(project: ProjectCreate, username: str = Depends(get_current_user)):
    """Create a new project with its integration URLs."""
    try:
        doc = {
            "name": project.name,
            "owner": username,
            "trello_board_url": project.trello_board_url,
            "n8n_trello_webhook": project.n8n_trello_webhook,
            "n8n_get_cards_url": project.n8n_get_cards_url,
            "n8n_slack_webhook": project.n8n_slack_webhook,
            "created_at": datetime.now()
        }
        result = projects_collection.insert_one(doc)
        return {"msg": f"Project '{project.name}' created", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects")
def get_projects(username: str = Depends(get_current_user)):
    """List all projects for the authenticated user."""
    try:
        projects = list(projects_collection.find(
            {"owner": username},
            {"_id": 0}
        ).sort("created_at", -1))
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/projects/{project_name}")
def delete_project(project_name: str, username: str = Depends(get_current_user)):
    """Delete a project by name."""
    try:
        projects_collection.delete_one({"name": project_name, "owner": username})
        return {"msg": f"Project '{project_name}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger-workflow")
def trigger_workflow(workflow_id: str):
    """
    Called when user clicks 'Run Workflow'.
    """
    # Logic to hit n8n webhook can go here
    return {"status": "triggered", "workflow_id": workflow_id}

# ==========================================
# 🔐 RBAC ENDPOINTS
# ==========================================

@app.get("/user/role")
def get_user_role(username: str = Depends(get_current_user)):
    """Returns the current user's role."""
    user = users_collection.find_one({"username": username}, {"role": 1, "_id": 0})
    return {"role": user.get("role", "developer") if user else "developer"}

@app.put("/user/role/{target_username}")
def update_user_role(target_username: str, role: str, user_info: dict = Depends(require_role("admin"))):
    """Admin-only: Change a user's role."""
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")
    users_collection.update_one({"username": target_username}, {"$set": {"role": role}})
    return {"msg": f"Updated {target_username} to role: {role}"}

# ==========================================
# 📦 EPIC → STORY → TASK HIERARCHY
# ==========================================

@app.post("/epics")
def create_epic(epic: EpicCreate, user_info: dict = Depends(require_role("admin", "pm"))):
    """Create a new Epic. PM/Admin only."""
    doc = {
        "name": epic.name,
        "description": epic.description,
        "project_id": epic.project_id,
        "color": epic.color,
        "status": "active",
        "created_by": user_info["username"],
        "created_at": datetime.now()
    }
    result = epics_collection.insert_one(doc)
    return {"msg": f"Epic '{epic.name}' created", "id": str(result.inserted_id)}

@app.get("/epics")
def get_epics(username: str = Depends(get_current_user)):
    """List all epics."""
    epics = list(epics_collection.find({}, {"_id": 0}))
    # Add string ID for frontend
    all_epics = []
    for e in epics_collection.find({}):
        e["id"] = str(e["_id"])
        del e["_id"]
        all_epics.append(e)
    return all_epics

@app.put("/epics/{epic_id}")
def update_epic(epic_id: str, epic: EpicUpdate, user_info: dict = Depends(require_role("admin", "pm"))):
    """Update an epic."""
    update_data = {k: v for k, v in epic.dict().items() if v is not None}
    epics_collection.update_one({"_id": ObjectId(epic_id)}, {"$set": update_data})
    return {"msg": "Epic updated"}

@app.delete("/epics/{epic_id}")
def delete_epic(epic_id: str, user_info: dict = Depends(require_role("admin", "pm"))):
    """Delete an epic and all its stories/tasks."""
    epics_collection.delete_one({"_id": ObjectId(epic_id)})
    stories_collection.delete_many({"epic_id": epic_id})
    tasks_collection.delete_many({"epic_id": epic_id})
    return {"msg": "Epic and all children deleted"}

# --- STORIES ---
@app.post("/stories")
def create_story(story: StoryCreate, user_info: dict = Depends(require_role("admin", "pm"))):
    """Create a story under an epic."""
    doc = {
        "name": story.name,
        "description": story.description,
        "epic_id": story.epic_id,
        "story_points": story.story_points,
        "assigned_to": story.assigned_to,
        "status": "todo",
        "created_by": user_info["username"],
        "created_at": datetime.now()
    }
    result = stories_collection.insert_one(doc)
    return {"msg": f"Story '{story.name}' created", "id": str(result.inserted_id)}

@app.get("/stories")
def get_stories(epic_id: str = None, username: str = Depends(get_current_user)):
    """List stories, optionally filtered by epic_id."""
    query = {"epic_id": epic_id} if epic_id else {}
    all_stories = []
    for s in stories_collection.find(query):
        s["id"] = str(s["_id"])
        del s["_id"]
        all_stories.append(s)
    return all_stories

@app.put("/stories/{story_id}")
def update_story(story_id: str, story: StoryUpdate, user_info: dict = Depends(require_role("admin", "pm"))):
    """Update a story."""
    update_data = {k: v for k, v in story.dict().items() if v is not None}
    stories_collection.update_one({"_id": ObjectId(story_id)}, {"$set": update_data})
    return {"msg": "Story updated"}

# --- TASKS (Hierarchy) ---
@app.post("/tasks")
def create_task(task: TaskItemCreate, username: str = Depends(get_current_user)):
    """Create a task under a story/epic."""
    doc = {
        "name": task.name,
        "description": task.description,
        "story_id": task.story_id,
        "epic_id": task.epic_id,
        "assigned_to": task.assigned_to,
        "status": task.status,
        "due_date": task.due_date,
        "start_date": task.start_date,
        "estimated_hours": task.estimated_hours,
        "actual_hours": 0,
        "depends_on": task.depends_on,
        "created_by": username,
        "created_at": datetime.now()
    }
    result = tasks_collection.insert_one(doc)
    return {"msg": f"Task '{task.name}' created", "id": str(result.inserted_id)}

@app.get("/tasks")
def get_tasks(story_id: str = None, epic_id: str = None, username: str = Depends(get_current_user)):
    """List tasks, optionally filtered."""
    query = {}
    if story_id: query["story_id"] = story_id
    if epic_id: query["epic_id"] = epic_id
    all_tasks = []
    for t in tasks_collection.find(query):
        t["id"] = str(t["_id"])
        del t["_id"]
        all_tasks.append(t)
    return all_tasks

@app.put("/tasks/{task_id}")
def update_task(task_id: str, task: TaskItemUpdate, username: str = Depends(get_current_user)):
    """Update a task."""
    update_data = {k: v for k, v in task.dict().items() if v is not None}
    tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": update_data})
    return {"msg": "Task updated"}

# --- WORK BREAKDOWN TREE ---
@app.get("/work-breakdown")
def get_work_breakdown(username: str = Depends(get_current_user)):
    """Returns the full Epic → Story → Task tree."""
    tree = []
    for epic in epics_collection.find({}):
        epic_id = str(epic["_id"])
        epic_node = {
            "id": epic_id,
            "name": epic.get("name"),
            "description": epic.get("description", ""),
            "color": epic.get("color", "#6C5DD3"),
            "status": epic.get("status", "active"),
            "type": "epic",
            "stories": []
        }
        
        for story in stories_collection.find({"epic_id": epic_id}):
            story_id = str(story["_id"])
            story_node = {
                "id": story_id,
                "name": story.get("name"),
                "description": story.get("description", ""),
                "story_points": story.get("story_points", 0),
                "assigned_to": story.get("assigned_to", "Unassigned"),
                "status": story.get("status", "todo"),
                "type": "story",
                "tasks": []
            }
            
            for task in tasks_collection.find({"story_id": story_id}):
                task_node = {
                    "id": str(task["_id"]),
                    "name": task.get("name"),
                    "description": task.get("description", ""),
                    "assigned_to": task.get("assigned_to", "Unassigned"),
                    "status": task.get("status", "todo"),
                    "due_date": task.get("due_date"),
                    "start_date": task.get("start_date"),
                    "estimated_hours": task.get("estimated_hours", 0),
                    "actual_hours": task.get("actual_hours", 0),
                    "depends_on": task.get("depends_on", []),
                    "type": "task"
                }
                story_node["tasks"].append(task_node)
            
            epic_node["stories"].append(story_node)
        
        # Also get tasks directly under epic (no story)
        for task in tasks_collection.find({"epic_id": epic_id, "story_id": ""}):
            task_node = {
                "id": str(task["_id"]),
                "name": task.get("name"),
                "assigned_to": task.get("assigned_to", "Unassigned"),
                "status": task.get("status", "todo"),
                "due_date": task.get("due_date"),
                "start_date": task.get("start_date"),
                "type": "task"
            }
            epic_node["stories"].append(task_node)
        
        tree.append(epic_node)
    
    return tree

# ==========================================
# 📊 GANTT CHART DATA ENDPOINT
# ==========================================

@app.get("/gantt-data")
def get_gantt_data(username: str = Depends(get_current_user)):
    """Returns all tasks formatted for Gantt chart rendering with critical path."""
    gantt_items = []
    all_tasks_map = {}
    
    # 1. Build task list from MongoDB hierarchy
    for task in tasks_collection.find({}):
        task_id = str(task["_id"])
        
        # Look up epic name
        epic_name = "Unassigned"
        epic_color = "#6C5DD3"
        if task.get("epic_id"):
            epic = epics_collection.find_one({"_id": ObjectId(task["epic_id"])})
            if epic:
                epic_name = epic.get("name", "Unassigned")
                epic_color = epic.get("color", "#6C5DD3")
        
        item = {
            "id": task_id,
            "name": task.get("name", "Task"),
            "start_date": task.get("start_date"),
            "end_date": task.get("due_date"),
            "owner": task.get("assigned_to", "Unassigned"),
            "status": task.get("status", "todo"),
            "epic_name": epic_name,
            "epic_color": epic_color,
            "depends_on": task.get("depends_on", []),
            "estimated_hours": task.get("estimated_hours", 0),
            "is_critical_path": False
        }
        gantt_items.append(item)
        all_tasks_map[task_id] = item
    
    # 2. Also pull in Trello cards as gantt items (for backward compatibility)
    try:
        if N8N_GET_ALL_CARDS_URL:
            response = requests.get(N8N_GET_ALL_CARDS_URL, timeout=10)
            if response.status_code == 200:
                raw_data = response.json()
                cards = raw_data if isinstance(raw_data, list) else raw_data.get("data", [])
                trello_done_list = os.getenv("TRELLO_DONE_LIST_ID", "")
                trello_in_progress_list = os.getenv("TRELLO_IN_PROGRESS_LIST_ID", "")
                
                for c in cards:
                    if isinstance(c, dict) and "json" in c: c = c["json"]
                    if not isinstance(c, dict): continue
                    if not c.get("due"): continue
                    
                    card_id = c.get("id", "")
                    # Skip if already in tasks_collection
                    if card_id in all_tasks_map: continue
                    
                    # Determine status from list
                    list_id = c.get("idList", "")
                    status = "todo"
                    if list_id == trello_done_list or c.get("dueComplete"):
                        status = "done"
                    elif list_id == trello_in_progress_list:
                        status = "in_progress"
                    
                    # Extract owner from [Owner] prefix
                    card_name = c.get("name", "")
                    owner = "Unassigned"
                    clean_name = card_name
                    if "[" in card_name and "]" in card_name:
                        owner = card_name.split("]")[0].replace("[", "").strip()
                        clean_name = card_name.split("]")[1].strip()
                    
                    # Parse dependencies from description
                    deps = []
                    desc = c.get("desc", "")
                    if "Blocked By:" in desc:
                        try:
                            blocker_part = desc.split("Blocked By:")[1].split("\n")[0]
                            blocker_part = blocker_part.replace("*", "").strip()
                            deps = [b.strip() for b in blocker_part.split(",") if b.strip()]
                        except: pass
                    
                    # Calculate start date (due - duration estimate)
                    try:
                        due_dt = datetime.fromisoformat(c["due"].replace("Z", ""))
                        # Estimate start from duration rules
                        days = 2
                        for k, v in DURATION_RULES.items():
                            if k in clean_name.lower(): days = max(days, v)
                        start_dt = due_dt - timedelta(days=days)
                        start_str = start_dt.strftime("%Y-%m-%d")
                        end_str = due_dt.strftime("%Y-%m-%d")
                    except:
                        start_str = None
                        end_str = None
                    
                    item = {
                        "id": card_id,
                        "name": clean_name,
                        "start_date": start_str,
                        "end_date": end_str,
                        "owner": owner,
                        "status": status,
                        "epic_name": "Trello Board",
                        "epic_color": "#0079BF",
                        "depends_on": deps,
                        "estimated_hours": 0,
                        "is_critical_path": False
                    }
                    gantt_items.append(item)
                    all_tasks_map[card_id] = item
    except Exception as e:
        print(f"Gantt Trello fetch error: {e}")
    
    # 3. Compute Critical Path (longest dependency chain)
    def get_chain_length(item_id, visited=None):
        if visited is None: visited = set()
        if item_id in visited: return 0
        visited.add(item_id)
        item = all_tasks_map.get(item_id)
        if not item: return 0
        deps = item.get("depends_on", [])
        if not deps: return 1
        max_dep_length = 0
        for dep_name in deps:
            # Find task by name match
            for tid, t in all_tasks_map.items():
                if dep_name.lower() in t.get("name", "").lower():
                    dep_length = get_chain_length(tid, visited.copy())
                    max_dep_length = max(max_dep_length, dep_length)
        return 1 + max_dep_length
    
    # Find max chain and mark critical path
    max_chain = 0
    chain_lengths = {}
    for item in gantt_items:
        length = get_chain_length(item["id"])
        chain_lengths[item["id"]] = length
        max_chain = max(max_chain, length)
    
    # Mark tasks on the critical path (longest chain)
    if max_chain > 1:
        for item in gantt_items:
            if chain_lengths.get(item["id"], 0) == max_chain:
                item["is_critical_path"] = True
    
    return {"tasks": gantt_items, "total": len(gantt_items)}

# ==========================================
# 🏃 SPRINT MANAGEMENT ENDPOINTS
# ==========================================

@app.post("/sprints")
def create_sprint(sprint: SprintCreate, user_info: dict = Depends(require_role("admin", "pm"))):
    """Create a new sprint. PM/Admin only."""
    doc = {
        "name": sprint.name,
        "goal": sprint.goal,
        "start_date": sprint.start_date,
        "end_date": sprint.end_date,
        "capacity_hours": sprint.capacity_hours,
        "project_id": sprint.project_id,
        "status": "planning",  # planning, active, completed
        "created_by": user_info["username"],
        "created_at": datetime.now()
    }
    result = sprints_collection.insert_one(doc)
    return {"msg": f"Sprint '{sprint.name}' created", "id": str(result.inserted_id)}

@app.get("/sprints")
def get_sprints(project_id: str = "default", username: str = Depends(get_current_user)):
    """List all sprints for a project."""
    all_sprints = []
    for s in sprints_collection.find({"project_id": project_id}):
        s["id"] = str(s["_id"])
        del s["_id"]
        
        # Serialize datetime fields
        if "created_at" in s and hasattr(s["created_at"], "isoformat"):
            s["created_at"] = s["created_at"].isoformat()
        
        # Dynamically calculate sprint metrics
        tasks_in_sprint = list(tasks_collection.find({"sprint_id": s["id"]}))
        s["committed_tasks"] = len(tasks_in_sprint)
        s["committed_hours"] = sum(t.get("estimated_hours", 0) for t in tasks_in_sprint)
        s["completed_tasks"] = sum(1 for t in tasks_in_sprint if t.get("status") == "done")
        s["completed_hours"] = sum(t.get("actual_hours", 0) for t in tasks_in_sprint if t.get("status") == "done")
        
        all_sprints.append(s)
        
    # Sort sprints by start_date
    all_sprints.sort(key=lambda x: x.get("start_date", ""))
    return all_sprints

@app.put("/sprints/{sprint_id}")
def update_sprint(sprint_id: str, sprint: SprintUpdate, user_info: dict = Depends(require_role("admin", "pm"))):
    """Update a sprint."""
    update_data = {k: v for k, v in sprint.dict().items() if v is not None}
    sprints_collection.update_one({"_id": ObjectId(sprint_id)}, {"$set": update_data})
    return {"msg": "Sprint updated"}

@app.get("/sprints/{sprint_id}/burndown")
def get_sprint_burndown(sprint_id: str, username: str = Depends(get_current_user)):
    """Calculate the real burndown chart data for a specific sprint."""
    sprint = sprints_collection.find_one({"_id": ObjectId(sprint_id)})
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
        
    tasks = list(tasks_collection.find({"sprint_id": sprint_id}))
    total_estimated = sum(t.get("estimated_hours", 0) for t in tasks)
    
    # Generate dates between start and end
    start_dt = datetime.fromisoformat(sprint["start_date"].replace("Z", ""))
    end_dt = datetime.fromisoformat(sprint["end_date"].replace("Z", ""))
    current_dt = start_dt
    
    dates = []
    ideal_line = []
    actual_line = []
    
    total_days = (end_dt - start_dt).days
    if total_days <= 0: total_days = 1
    
    # Get all time logs for tasks in this sprint
    task_names = [t.get("name") for t in tasks]
    time_logs = list(time_logs_collection.find({"task_name": {"$in": task_names}}))
    
    remaining = total_estimated
    day_count = 0
    now_dt = datetime.now()
    
    while current_dt <= end_dt:
        date_str = current_dt.strftime("%Y-%m-%d")
        dates.append(current_dt.strftime("%b %d"))
        
        # Ideal line
        ideal_val = total_estimated - (total_estimated / total_days) * day_count
        ideal_line.append(max(0, ideal_val))
        
        # Actual line
        if current_dt.date() <= now_dt.date():
            # Sum hours logged ON this day for these tasks
            logs_today = [l for l in time_logs if l["timestamp"].strftime("%Y-%m-%d") == date_str]
            hours_burned = sum(l.get("hours", 0) for l in logs_today)
            remaining -= hours_burned
            actual_line.append(max(0, remaining))
        else:
            actual_line.append(None) # Future dates
            
        current_dt += timedelta(days=1)
        day_count += 1
        
    return {
        "sprint_name": sprint["name"],
        "total_estimated": total_estimated,
        "labels": dates,
        "ideal": ideal_line,
        "actual": actual_line
    }

@app.get("/")
def health_check():
    health_status = {
        "status": "AI is awake",
        "database": "connected" if (db is not None and users_collection is not None) else "disconnected",
        "mongodb_uri_set": bool(MONGO_URI),
        "secret_key_set": bool(SECRET_KEY and SECRET_KEY != "default_secret"),
    }
    if db is not None:
        try:
            db.command("ping")
            health_status["database"] = "connected"
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
    return health_status

