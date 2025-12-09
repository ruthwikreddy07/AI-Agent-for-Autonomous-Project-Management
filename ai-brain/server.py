import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from pymongo import MongoClient
from passlib.context import CryptContext
from jose import jwt
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from pinecone import Pinecone
from dotenv import load_dotenv

# --- IMPORT CALENDAR TOOL ---
try:
    from calendar_tool import create_meeting
except ImportError:
    print("⚠️ Warning: calendar_tool.py not found. Scheduling will not work.")
    def create_meeting(*args, **kwargs): return "Error: calendar_tool.py missing"

# ==========================================
# 1. CONFIGURATION & SECRETS
# ==========================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_HOST = os.getenv("PINECONE_HOST")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret")
ALGORITHM = "HS256"

# Webhooks
N8N_TRELLO_URL = os.getenv("N8N_TRELLO_URL")
N8N_SLACK_URL = os.getenv("N8N_SLACK_URL")
N8N_GET_CARDS_URL = os.getenv("N8N_GET_CARDS_URL")
N8N_ALERT_URL = os.getenv("N8N_ALERT_URL") 

# Trello API
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")

TRELLO_LABELS = {
    "bug" : os.getenv("PASTE_RED_LABEL_ID"),
    "feature": os.getenv("PASTE_GREEN_LABEL_ID"),
    "urgent": os.getenv("PASTE_YELLOW_LABEL_ID")
}

os.environ["GROQ_API_KEY"] = GROQ_API_KEY
# ADD THIS:
HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

def generate_embedding(text: str):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    # We use "wait_for_model" so it doesn't fail if the model is cold
    response = requests.post(HF_API_URL, headers=headers, json={"inputs": text, "options": {"wait_for_model": True}})
    return response.json()

DURATION_RULES = {"ui": 3, "design": 3, "api": 5, "database": 4, "test": 2, "deploy": 1, "fix": 1, "meeting": 0}

app = FastAPI()

# CORS Configuration - Must be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",  # Angular dev server
        "https://ai-agent-for-project-management.onrender.com",  # 👈 YOUR FRONTEND URL
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Global exception handler to ensure CORS headers are always included
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": "https://ai-agent-for-project-management.onrender.com",
            "Access-Control-Allow-Credentials": "true",
        }
    )
# Database
client = None
db = None
users_collection = None
employees_collection = None

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["ai_project_manager"]
    users_collection = db["users"]
    employees_collection = db["employees"]
    # Test connection
    client.admin.command('ping')
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")
    print(f"❌ MONGO_URI: {MONGO_URI[:20]}..." if MONGO_URI else "❌ MONGO_URI not set")

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Employee(BaseModel):
    name: str
    role: str
    skills: List[str]
    email: str 
    trello_id: Optional[str] = "" 

class User(BaseModel):
    username: str
    password: str
class UserRequest(BaseModel):
    message: str

# --- MEMORY CONFIGURATION ---

# 1. Pinecone (Database)
pc = Pinecone(api_key=PINECONE_API_KEY)
memory_index = pc.Index(name="project-memory", host=PINECONE_HOST)

# 2. LLM (The Brain)
llm = ChatGroq(model="llama-3.1-8b-instant") 

# 3. Embedding (The API - Replaces SentenceTransformer)
HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

def generate_embedding(text: str):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(HF_API_URL, headers=headers, json={"inputs": text, "options": {"wait_for_model": True}})
    return response.json()

# Helpers
def get_trello_id_by_email(email: str) -> str:
    if not TRELLO_API_KEY or not TRELLO_TOKEN: return ""
    url = "https://api.trello.com/1/search/members/"
    try:
        resp = requests.get(url, params={'query': email, 'key': TRELLO_API_KEY, 'token': TRELLO_TOKEN, 'limit': 1})
        if resp.status_code == 200 and resp.json(): return resp.json()[0]['id']
    except: pass
    return ""

def get_dynamic_roster():
    try:
        employees = list(employees_collection.find({}, {"_id": 0}))
        if not employees: return "No employees found."
        roster = "TEAM ROSTER:\n"
        for emp in employees:
            roster += f"- {emp['name']} ({emp['role']}) - Skills: {', '.join(emp['skills'])}\n"
        return roster
    except: return "Error."

def auto_assign_owner(task_name, task_desc):
    text = (task_name + " " + task_desc).lower()
    try:
        for emp in list(employees_collection.find({}, {"_id": 0})):
            for skill in emp['skills']:
                if skill.lower() in text: return emp['name']
    except: pass
    return "Unassigned"

def get_trello_id_from_db(name):
    try:
        emp = employees_collection.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if emp: return emp.get("trello_id", "")
    except: pass
    return ""

def estimate_due_date(task_name):
    days = 2
    for k, v in DURATION_RULES.items():
        if k in task_name.lower(): days = max(days, v)
    return (datetime.now() + timedelta(days=days)).isoformat()

chat_history = []
pending_plan = None
current_risks = []


def refresh_system_prompt():
    global chat_history

    roster = get_dynamic_roster()

    prompt = f"""
You are an Intelligent AI Project Manager.

{roster}


===========================
⚙️  TOOLKIT
===========================

1️⃣  **execute_project_plan**
    - Use this ONLY for COMPLEX requests.
    - Trigger words: "Build", "Create", "Launch", "Develop", "Plan".
    - Examples:
        • "Build a mobile app"
        • "Create backend architecture"
        • "Plan the whole dashboard system"
    - Automatically produces a *multi-task project plan*.
    - Requires human approval.

2️⃣  **create_task_in_trello**
    - Use ONLY for simple, single tasks.
    - Examples:
        • "Fix a bug"
        • "Update UI color"
        • "Add a card for documentation"

3️⃣  **schedule_meeting_tool**
    - Use when user says:
        • "Schedule"
        • "Book"
        • "Set up meeting"

4️⃣  **check_project_status**
    - Use for project progress checks, risks, summaries.

=== 📌 CRITICAL SELECTION RULES ===
1. IF user says "Plan", "Design", "Build", "Create App", or asks for a "Feature":
   -> YOU MUST USE 'execute_project_plan'.
   -> Do NOT use 'create_task_in_trello'.
   -> Break the request down into at least 3 sub-tasks.

2. IF user says "Add task", "Fix bug", "Update card":
   -> Use 'create_task_in_trello'.

3. IF user says "Schedule", "Book":
   -> Use 'schedule_meeting_tool'.


===========================
📌  CRITICAL DECISION RULES
===========================


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
🎯  BEHAVIOR EXPECTATIONS
===========================

- Always think step-by-step.
- Always choose the correct tool.
- Never mix complex plans with simple tasks.
- Ensure clean JSON formatting.

"""

    chat_history = [SystemMessage(content=prompt)]


# ==========================================
# 3. TOOLS (FIXED DOCSTRINGS)
# ==========================================

def internal_create_trello(name, desc, owner, start_hour=10):
    # 1. Calculate Date & IDs
    due_date = estimate_due_date(name)

    # Get Employee Data (ID + Email)
    emp_data = {}
    try:
        emp_data = employees_collection.find_one({"name": {"$regex": f"^{owner}$", "$options": "i"}})
    except:
        pass

    member_id = emp_data.get("trello_id", "") if emp_data else ""
    emp_email = emp_data.get("email", "") if emp_data else ""

    # --- DEBUG PRINTS ---
    print(f"🧐 DEBUG: Task '{name}' assigned to '{owner}'")
    print(f"🧐 DEBUG: Found Email: '{emp_email}'")
    # --------------------

    if not member_id and owner != "Unassigned":
        name = f"[{owner}] {name}"

    # 2. Label & Urgency Detection
    label_id = ""
    is_urgent = False
    name_lower = name.lower()

    if "bug" in name_lower or "fix" in name_lower:
        label_id = TRELLO_LABELS.get("bug", "")
        if "critical" in name_lower or "urgent" in name_lower or "crash" in name_lower:
            is_urgent = True
    elif "feature" in name_lower:
        label_id = TRELLO_LABELS.get("feature", "")

    # 3. Create Trello Card
    full_desc = f"👤 **ASSIGNED TO:** {owner}\n\n{desc}"
    payload = {
        "task_name": name,
        "description": full_desc,
        "due_date": due_date,
        "member_id": member_id,
        "label_id": label_id
    }

    trello_success = False
    try:
        resp = requests.post(N8N_TRELLO_URL, json=payload)
        if resp.status_code == 200:
            trello_success = True
    except:
        pass

    # 4. AUTO-SCHEDULE + ALERT
    calendar_msg = ""
    if trello_success:
        # A. Calendar Auto-Schedule
        try:
            due_dt = datetime.fromisoformat(due_date)
            focus_start = due_dt - timedelta(days=1)
            focus_start = focus_start.replace(hour=start_hour, minute=0, second=0, microsecond=0)

            focus_title = f"⚡ Focus Time: {name}"
            result = create_meeting(
                focus_title,
                f"Work on Trello Card: {name}",
                focus_start.isoformat(),
                is_video_call=False,
            )

            actual_time = focus_start.strftime('%A at %I:%M %p')

            if "(Booked at " in str(result):
                booked_time = str(result).split("(Booked at ")[1].replace(")", "")
                actual_time = f"{focus_start.strftime('%A')} at {booked_time}"

            calendar_msg = f" (📅 {actual_time})"

            if "Success" in str(result):
                try:
                    clean_link = (
                        str(result).split(" (Booked")[0]
                        .replace("Success! Link: ", "")
                        .strip()
                    )
                except:
                    clean_link = str(result)

                slack_msg = (
                    f"📅 *AUTO-SCHEDULED:* {focus_title}\n"
                    f"👤 *Assigned To:* {owner}\n"
                    f"⏰ *Focus Time:* {actual_time}\n"
                    f"🎯 *Deadline:* {due_dt.strftime('%Y-%m-%d')}\n"
                    f"🔗 *Calendar Link:* {clean_link}"
                )
                requests.post(N8N_SLACK_URL, json={"message": slack_msg})

        except Exception as e:
            print(f"Auto-schedule failed: {e}")

        # B. Emergency Alert (Only for urgent tasks)
        if is_urgent and emp_email:
            print(f"🚀 DEBUG: Attempting to send email to {emp_email} via {N8N_ALERT_URL}")
            alert_payload = {
                "task_name": name,
                "owner_name": owner,
                "email": emp_email
            }
            try:
                email_resp = requests.post(N8N_ALERT_URL, json=alert_payload)
                print(f"📬 DEBUG: n8n Response Code: {email_resp.status_code}")
                print(f"📬 DEBUG: n8n Response Body: {email_resp.text}")
            except:
                print(f"❌ DEBUG: Failed to connect to n8n: {e}")
            calendar_msg += " (🚨 Urgent Email Sent!)"
        elif is_urgent and not emp_email:
            print("❌ DEBUG: Task is Urgent, but NO EMAIL found for this user in Database.")

    return trello_success, calendar_msg



@tool
def create_task_in_trello(task_name: str, description: str = "", owner: str = "Auto"):
    """Creates a single task in Trello. If owner is 'Auto', it will be auto-assigned."""
    if owner == "Auto": owner = auto_assign_owner(task_name, description)
    success, cal_msg = internal_create_trello(task_name, description, owner)
    
    if success:
        return f"Success! Created task for {owner}.{cal_msg}"
    return "Failed to create task."

@tool
def send_slack_announcement(message: str):
    """
    Sends a public message to the Slack channel. 
    Use this to announce updates, risks, or completed tasks to the team.
    """
    try:
        requests.post(N8N_SLACK_URL, json={"message": message})
        return "Success."
    except: return "Failed."

@tool
def consult_project_memory(query: str):
    """
    Searches the project database for relevant information. 
    Use this when the user asks about the budget, requirements, or past decisions.
    """
    try:
        # OLD: v = embedding_model.encode(query).tolist()
        # NEW: Use the API function
        v = generate_embedding(query)
        
        # Handle potential API quirks (sometimes it returns a list of lists)
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], list):
            v = v[0]
            
        if isinstance(v, dict) and "error" in v:
            return f"Error from HuggingFace: {v['error']}"

        r = memory_index.query(vector=v, top_k=3, include_metadata=True)
        return "\n".join([f"- {m['metadata']['text']}" for m in r['matches']])
    except Exception as e:
        return f"Memory Error: {e}"

@tool
def schedule_meeting_tool(summary: str, description: str, start_time: str):
    """
    Schedules a Google Calendar meeting AND notifies Slack.
    If the user specified an exact time, it will try to book at that exact time.
    If the time is busy, it will return an error (user can choose another time).
    Args:
        summary: Title of the meeting (e.g. "Project Kickoff")
        description: Details or agenda for the meeting
        start_time: ISO format date string (e.g. "2025-12-01T10:00:00")
    """
    print(f"📅 CALENDAR: Scheduling '{summary}' at {start_time}")
    
    # 1. Create the meeting in Google Calendar
    # strict_time=True means: respect the exact time user requested, don't auto-reschedule
    result = create_meeting(summary, description, start_time, is_video_call=True, strict_time=True)
    
    # 2. If successful, Notify Slack automatically!
    if "Success" in str(result):
        # Extract Link
        clean_link = str(result).split(" (Booked")[0].replace("Success! Link: ", "").strip()
        time_part = str(result).split("(Booked at ")[1].replace(")", "")
        
        slack_msg = (
            f"📅 *NEW MEETING SCHEDULED:*\n"
            f"📌 *Event:* {summary}\n"
            f"⏰ *Time:* {time_part}\n"
            f"📹 *Video Link:* {clean_link}"  # Says "Video Link"
        )
        try: requests.post(N8N_SLACK_URL, json={"message": slack_msg})
        except: pass
            
    return result

@tool
def execute_project_plan(goal: str, tasks: str):
    """Generates a multi-step plan. Tasks must be a JSON string."""
    global pending_plan
    try:
        # 1. Parse the JSON
        raw_data = json.loads(tasks)
        clean_tasks = []
        
        # 2. Handle if AI wraps it in {"tasks": [...]}
        if isinstance(raw_data, dict) and "tasks" in raw_data: 
            raw_data = raw_data["tasks"]
            
        # 3. Handle if AI returns a simple list of strings
        if isinstance(raw_data, list):
            for t in raw_data:
                # FIX: If t is a string, convert it to an object
                if isinstance(t, str):
                    t = {"name": t, "desc": "Auto-generated task", "owner": "Unassigned"}
                
                # Now it is safe to use .get()
                if "owner" not in t or t["owner"] == "Unassigned":
                    t["owner"] = auto_assign_owner(t.get("name", ""), t.get("desc", ""))
                
                clean_tasks.append(t)
        else:
            return "Error: AI returned invalid JSON structure."

        pending_plan = {"goal": goal, "tasks": clean_tasks}
        return "PLAN_STAGED"

    except Exception as e: return f"Error: {e}"

@tool
def check_project_status(dummy: str = ""):
    """
    Checks the Trello board for overdue tasks and risks.
    Use this when the user asks for a status report or risk analysis.
    """
    global current_risks
    try:
        response = requests.get(N8N_GET_CARDS_URL)
        cards = response.json()
        risks = []
        today = datetime.now()
        for c in cards:
            if 'json' in c: c = c['json']
            if c.get('due'):
                try:
                    d = datetime.fromisoformat(c['due'].replace('Z', '+00:00')).replace(tzinfo=None)
                    if today > d: risks.append(f"⚠️ OVERDUE: '{c['name']}'")
                except: pass
        current_risks = risks
        if not risks: return "✅ ALL GOOD."
        requests.post(N8N_SLACK_URL, json={"message": f"🚨 RISK REPORT:\n" + "\n".join(risks)})
        return "Risks Found"
    except Exception as e: return f"Error: {e}"

llm_with_tools = llm.bind_tools([create_task_in_trello, send_slack_announcement, consult_project_memory, execute_project_plan, check_project_status,schedule_meeting_tool])


# ==========================================
# 4. ENDPOINTS
# ==========================================
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # Check database connection
        if not users_collection or not db:
            print("❌ Database not initialized")
            raise HTTPException(
                status_code=500, 
                detail="Database connection failed. Please check server logs."
            )
        
        # Test database connection
        try:
            db.command('ping')
        except Exception as db_err:
            print(f"❌ Database ping failed: {db_err}")
            raise HTTPException(
                status_code=500,
                detail=f"Database connection error: {str(db_err)}"
            )
        
        # Check SECRET_KEY
        if not SECRET_KEY or SECRET_KEY == "default_secret":
            print("❌ SECRET_KEY not configured properly")
            raise HTTPException(
                status_code=500,
                detail="Server configuration error: SECRET_KEY not set"
            )
        
        # Find user
        print(f"🔍 Attempting login for user: {form_data.username}")
        user = users_collection.find_one({"username": form_data.username})
        
        if not user:
            print(f"❌ User not found: {form_data.username}")
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        
        # Verify password
        if not pwd_context.verify(form_data.password, user["password"]):
            print(f"❌ Invalid password for user: {form_data.username}")
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        
        # Generate token
        token = jwt.encode({"sub": user["username"]}, SECRET_KEY, algorithm=ALGORITHM)
        print(f"✅ Login successful for user: {form_data.username}")
        return {"access_token": token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Login error: {e}")
        print(f"❌ Traceback: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

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
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/employees")
def get_employees():
    return list(employees_collection.find({}, {"_id": 0}))
@app.post("/chat")
def chat_endpoint(req: UserRequest):
    chat_history.append(HumanMessage(content=req.message))
    response = llm_with_tools.invoke(chat_history)
    final = response.content
    approval = False
    plan_staged = False  # Track if we're in planning mode
    
    if response.tool_calls:
        # FIRST PASS: Check if execute_project_plan is called
        for tc in response.tool_calls:
            if tc["name"] == "execute_project_plan":
                res = execute_project_plan.invoke(tc["args"])
                if res == "PLAN_STAGED":
                    plan_staged = True
                    # --- PREVIEW GENERATOR ---
                    if pending_plan:
                        preview_lines = []
                        for t in pending_plan["tasks"]:
                            owner = t.get('owner', 'Unassigned')
                            name = t.get('name', 'Task')
                            preview_lines.append(f"• {name} → {owner}")
                        
                        preview_text = "\n".join(preview_lines)
                        final = f"I have drafted a plan:\n\n{preview_text}\n\nProceed?"; approval = True
                    else:
                        final = "Plan generated. Proceed?"; approval = True
                else: 
                    final = res
                break  # Exit after handling plan
        
        # SECOND PASS: Only execute other tools if NOT in planning mode
        if not plan_staged:
            for tc in response.tool_calls:
                fn = tc["name"]
                args = tc["args"]
                
                if fn == "create_task_in_trello": 
                    final = create_task_in_trello.invoke(args)
                elif fn == "send_slack_announcement": 
                    send_slack_announcement.invoke(args)
                    final = "Message sent."
                elif fn == "check_project_status": 
                    final = check_project_status.invoke(args)
                elif fn == "schedule_meeting_tool": 
                    final = schedule_meeting_tool.invoke(args)
                elif fn == "consult_project_memory":
                    res = consult_project_memory.invoke(args)
                    chat_history.append(response)
                    chat_history.append(HumanMessage(content=f"Memory: {res}"))
                    follow = llm_with_tools.invoke(chat_history)
                    final = follow.content
                    if follow.tool_calls and follow.tool_calls[0]["name"] == "execute_project_plan":
                        execute_project_plan.invoke(follow.tool_calls[0]["args"])
                        if pending_plan:
                            preview_lines = [f"• {t.get('name')} → {t.get('owner')}" for t in pending_plan["tasks"]]
                            final = f"Plan from memory:\n\n" + "\n".join(preview_lines) + "\n\nProceed?"
                            approval = True

    chat_history.append(response)
    return {"reply": final, "approval_required": approval}

@app.post("/approve")
def approve_plan():
    global pending_plan
    if not pending_plan: return {"status": "No plan."}
    results = []
    current_hour = 9
    for t in pending_plan["tasks"]:
        name = t.get("name", "Task")
        owner = t.get("owner", "Unassigned")
        desc = t.get("desc", "")
        
        success, cal_msg = internal_create_trello(name, desc, owner, start_hour=current_hour)
        
        status_text = f"Created: {name}"
        if cal_msg: status_text += " (+Calendar)"
        results.append(status_text)
        # Increment time by 2 hours for the next task
        current_hour += 2
        if current_hour > 17: current_hour = 9 # Reset to 9 AM if it gets too late (5 PM)

    requests.post(N8N_SLACK_URL, json={"message": f"✅ APPROVED: {pending_plan['goal']}\n" + "\n".join(results)})
    
    pending_plan = None
    return {"status": "Executed", "details": "\n".join(results)}

@app.post("/reject")
def reject_plan():
    global pending_plan
    pending_plan = None
    return {"status": "Cancelled"}

@app.get("/risks")
def get_risks(): return {"risks": current_risks}

@app.get("/")
def health_check():
    """Health check endpoint to verify server and database status"""
    health_status = {
        "status": "AI is awake",
        "database": "connected" if (db and users_collection) else "disconnected",
        "mongodb_uri_set": bool(MONGO_URI),
        "secret_key_set": bool(SECRET_KEY and SECRET_KEY != "default_secret")
    }
    
    # Test database connection
    if db:
        try:
            db.command('ping')
            health_status["database"] = "connected"
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
    
    return health_status