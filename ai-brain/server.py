# server.py  -- Combined Option A (HF embeddings, no sentence_transformers)
import os
import json
import requests
import time as time_module
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
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("⚠️ WARNING: GOOGLE_API_KEY is missing. Embeddings will fail.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

def generate_embedding(text: str):
    """
    Generates embeddings using Google Gemini (Free Tier).
    Output Dimension: 768
    """
    try:
        # Use the latest stable embedding model
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document" 
        )
        return result['embedding']
    except Exception as e:
        print(f"❌ Google Embedding Error: {e}")
        # Return a zero-vector fallback to prevent server crash, 
        # allowing the user to see the error in logs without 500ing immediately.
        raise RuntimeError(f"Google API Error: {str(e)}")
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
]
# optionally allow all in dev; in production prefer explicit origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins + ["*"],  # keep '*' if Render frontend domain dynamic; remove for strict prod
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["ai_project_manager"]
    users_collection = db["users"]
    employees_collection = db["employees"]
    chats_collection = db["chats"]
    client.admin.command("ping")
    print("✅ Connected to MongoDB")
except Exception as e:
    print("❌ MongoDB Error:", e)

# --------------------
# SECURITY & MODELS
# --------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Employee(BaseModel):
    name: str
    role: str
    skills: List[str]
    email: str
    trello_id: Optional[str] = ""
    rate: int = 50

class User(BaseModel):
    username: str
    password: str

class UserRequest(BaseModel):
    message: str
    session_id: str = "default_session"

class RejectRequest(BaseModel):
    reason: str = "No reason provided."

# --------------------
# MEMORY & LLM
# --------------------
pc = Pinecone(api_key=PINECONE_API_KEY)
memory_index = pc.Index(name="project-memory", host=PINECONE_HOST)
llm = ChatGroq(model="llama-3.1-8b-instant")

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
pending_plan = None
current_risks = []
current_budget_warning = ""
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
    - Argument 'budget': STRICTLY extract the dollar amount from the prompt.
    - 🛑 IF NO CURRENCY AMOUNT IS MENTIONED: You MUST pass 0. 
    - 🛑 DO NOT GUESS. DO NOT DEFAULT TO 1000.
    - If unsure, pass 0.
    - DO NOT GUESS. DO NOT ASSUME. Default is 0.
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

3️⃣  schedule_meeting_tool
    - 🚨 **HIGHEST PRIORITY**: If the user input contains "Schedule", "Book", or "Set up meeting", you MUST use this tool.
    - 🛑 **IF NO TIME IS PROVIDED**: Do NOT call the tool. Reply: "When would you like to schedule the meeting?"
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


4️⃣  **check_project_status**
    - Use for project progress checks, risks, summaries
    - 🛑 DO NOT use if the user asks to "Schedule" or "Book" a meeting.

5️⃣  consult_project_memory
    - Use when user asks specific questions about project facts (budget, deadlines, specs).
    - 🛑 DO NOT use if the user asks to "Schedule" or "Book" a meeting.

6️⃣  heal_project_schedule
    - Use when the user asks to "Heal", "Fix", "Repair", or "Reschedule" the project.
    - This tool automatically moves overdue tasks and resolves dependency conflicts in Trello.

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
    if "bug" in name_lower or "fix" in name_lower:
        label_id = TRELLO_LABELS.get("bug", "")
        if any(x in name_lower for x in ("critical", "urgent", "crash")): is_urgent = True
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
    """
    try:
        requests.post(N8N_SLACK_URL, json={"message": message}, timeout=5)
        return "Success."
    except Exception:
        return "Failed."

@tool
def consult_project_memory(query: str, username: str = "placeholder"):
    """Searches project documentation in the vector database."""
    try:
        v = generate_embedding(query)
        # HF sometimes returns [[...]] or [...]
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], list):
            v = v[0]
        if isinstance(v, dict) and "error" in v:
            return f"Error from HuggingFace: {v['error']}"
        r = memory_index.query(
            vector=v, 
            top_k=3, 
            include_metadata=True, 
            filter={"username": username} 
        )
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
            return f"✅ Available. The time {start_time} is free. Ask the user if they want to book it."
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
def execute_project_plan(goal: str, tasks: str | list, budget: float = 0):
    """Generates a multi-step plan. Tasks must be a JSON string. Budget is the max limit in dollars."""
    global pending_plan, current_budget_warning
    try:
        print(f"🧐 DEBUG RAW AI INPUT: {tasks}")
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
        current_budget_warning = "" # Reset warning

        # If user set a limit, check it and change the styling
        if target_budget > 0:
            if total_project_cost > target_budget:
                overrun = total_project_cost - target_budget
                
                # 🚨 RED ALERT STYLE
                budget_status_msg = (
                    f"🚨 **Total:** ${total_project_cost}\n"
                    f"⚠️ **Over Budget by:** ${overrun}"
                )
                current_budget_warning = f"🚨 **BUDGET OVERRUN:** Plan exceeds limit by ${overrun}!"
            
            else:
                remaining = target_budget - total_project_cost
                
                # ✅ GREEN SUCCESS STYLE
                budget_status_msg = (
                    f"✅ **Total:** ${total_project_cost}\n"
                    f"💰 **Under Budget:** ${remaining} remaining"
                )
                current_budget_warning = "" 
        else:
            # If no budget set, just show total neutral
            budget_status_msg = f"💵 **Total Project Cost:** ${total_project_cost}"
            current_budget_warning = ""

        # Save this pre-formatted message into the plan
        pending_plan = {
            "goal": goal, 
            "tasks": clean_tasks, 
            "budget_summary": budget_status_msg 
        }
        
        return "PLAN_STAGED"
    except Exception as e:
        print("❌ PLAN ERROR:", e)
        return f"Error: {e}"

@tool
def check_project_status(dummy: str = ""):
    """Checks Trello for overdue tasks AND active budget risks."""
    global current_risks, current_budget_warning
    try:
        risks = []
        try:
            print(f"🔍 Fetching cards from: {N8N_GET_ALL_CARDS_URL}")
            response = requests.get(N8N_GET_ALL_CARDS_URL, timeout=30)
            
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
        if current_budget_warning:
            risks.insert(0, current_budget_warning)

        current_risks = risks
        
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
    

# Bind tools
llm_with_tools = llm.bind_tools([create_task_in_trello, send_slack_announcement, consult_project_memory, execute_project_plan, check_project_status, schedule_meeting_tool,heal_project_schedule])

# ==========================================
# 🧠 MEMORY & PERSISTENCE LAYER
# ==========================================

# --------------------
# ENDPOINTS
# --------------------

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
    global pending_plan # Access the global variable
    
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
                res = execute_project_plan.invoke(args)
                if res == "PLAN_STAGED":
                    approval_required = True
                    if pending_plan:
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
        token = jwt.encode({"sub": user["username"]}, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print("Login error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register")
async def register(user: User):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Exists")
    users_collection.insert_one({"username": user.username, "password": pwd_context.hash(user.password)})
    return {"msg": "Created"}

@app.post("/employees")
def add_employee(emp: Employee):
    try:
        if not emp.trello_id and emp.email:
            emp.trello_id = get_trello_id_by_email(emp.email)
        employees_collection.insert_one(emp.dict())
        refresh_system_prompt()
        return {"msg": f"Added {emp.name} (ID: {emp.trello_id})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/employees")
def get_employees():
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
def get_full_history(session_id: str):
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
def approve_plan():
    global pending_plan
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
    budget_info = pending_plan.get("budget_summary", "No Budget Info")
    try:
        final_slack_msg = (
            f"✅ *APPROVED:* {pending_plan['goal']}\n"
            f"{budget_info}\n"  # <--- 🔥 ADDED THIS LINE
            f"----------------------------------\n"
            f"{chr(10).join(results)}"
        )
        requests.post(N8N_SLACK_URL, json={"message": final_slack_msg}, timeout=5)
    except:
        pass

    pending_plan = None
    return {"status": "Executed", "details": "\n".join(results)}



@app.post("/reject")
def reject_plan(req: Optional[RejectRequest] = None): # <--- Make it Optional
    global pending_plan, current_budget_warning, current_risks
    
    # 2. Clear the plan and the specific warning string
    pending_plan = None
    current_budget_warning = "" 
    
    # Handle the reason safely
    reason_text = req.reason if req else "User rejected the plan (No reason given)."
    
    # Feedback: Log why it was rejected so the AI context knows
    save_chat_message("system_plan_management", "user", f"❌ I rejected the plan. Reason: {reason_text}")

    # 3. Force refresh the risk list immediately
    check_project_status.invoke({"dummy": "refresh"})
    
    return {"status": "Cancelled"}

@app.get("/risks")
def get_risks():
    """
    Force a refresh of the project status immediately 
    so the Frontend gets live data on load.
    """
    # 1. Run the check logic explicitly!
    # This updates the 'current_risks' global variable
    check_project_status.invoke({"dummy": "refresh"})
    
    # 2. Return the freshly updated list
    return {"risks": current_risks}

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
