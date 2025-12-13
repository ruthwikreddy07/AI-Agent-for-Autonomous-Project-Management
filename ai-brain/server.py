# app.py  -- Combined Option A (HF embeddings, no sentence_transformers)
import os
import json
import requests
import time
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Request
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

# --- calendar_tool import (optional) ---
try:
    from calendar_tool import create_meeting
except ImportError:
    print("⚠️ Warning: calendar_tool.py not found. Scheduling will not work.")
    def create_meeting(*args, **kwargs): return "Error: calendar_tool.py missing"

load_dotenv()

# --------------------
# CONFIG & SECRETS
# --------------------
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

# Hugging Face embedding (lighter than local sentence_transformers)
HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

def generate_embedding(text: str):
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN not set")
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    resp = requests.post(HF_API_URL, headers=headers, json={"inputs": text, "options": {"wait_for_model": True}}, timeout=30)
    resp.raise_for_status()
    return resp.json()

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

# --------------------
# MEMORY & LLM
# --------------------
pc = Pinecone(api_key=PINECONE_API_KEY)
memory_index = pc.Index(name="project-memory", host=PINECONE_HOST)
llm = ChatGroq(model="llama-3.1-8b-instant")

# --------------------
# HELPERS
# --------------------
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
    text = (task_name + " " + task_desc).lower()
    try:
        for emp in list(employees_collection.find({}, {"_id": 0})):
            for skill in emp.get("skills", []):
                if skill.lower() in text:
                    return emp["name"]
    except Exception:
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
    
    # Note: The JSON example below uses {{ and }} to escape them for the f-string
    prompt = f"""
You are an Intelligent AI Project Manager.

{roster}

===========================
⚙️  TOOLKIT
===========================

1️⃣  **execute_project_plan**
    - Use this ONLY for COMPLEX requests.
    - Trigger words: "Build", "Create", "Launch", "Develop", "Plan".
    - **CRITICAL**: The 'tasks' argument MUST be a valid JSON string array.
    - Each item MUST be: {{ "name": "Task Title", "desc": "Short description", "owner": "Role Name" }}
    - "tool_cost" is optional: Estimate price of tools/software/vendors (e.g., 50 for a license).
    - Argument 'goal': Short description of the project.
    - Argument 'budget': Extract the budget amount from the user's prompt (e.g., if user says "$500" or "500 dollars", pass 500). If no budget is mentioned, pass 0.
    - Argument 'tasks': A valid JSON string array of tasks.
    - **CRITICAL**: The 'tasks' argument MUST be a valid JSON string array
    - Every task MUST include:
     - title
     - assigned_to
     - deadline
     - focus_time (1-hour slot)
    - Requires human approval.

2️⃣  **create_task_in_trello**
    - Use ONLY for simple, single tasks.

3️⃣  **schedule_meeting_tool**
    - Use when user says: "Schedule", "Book", "Set up meeting"

4️⃣  **check_project_status**
    - Use for project progress checks, risks, summaries

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

def internal_create_trello(name, desc, owner, start_hour=10):
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
    payload = {"task_name": name, "description": full_desc, "due_date": due_date, "member_id": member_id, "label_id": label_id}

    trello_success = False
    try:
        resp = requests.post(N8N_TRELLO_URL, json=payload, timeout=10)
        if resp.status_code == 200: trello_success = True
        else: print(f"❌ Trello Failed: {resp.text}", flush=True)
    except Exception as e:
        print(f"❌ Trello API Error: {e}", flush=True)

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
            time.sleep(2) 
            
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
    """Sends a message to the team Slack channel."""
    try:
        requests.post(N8N_SLACK_URL, json={"message": message}, timeout=5)
        return "Success."
    except Exception:
        return "Failed."

@tool
def consult_project_memory(query: str):
    """Searches project documentation in the vector database."""
    try:
        v = generate_embedding(query)
        # HF sometimes returns [[...]] or [...]
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
    Args:
        summary: Title of the meeting (e.g. "Project Kickoff")
        description: Details or agenda for the meeting
        start_time: ISO format date string (e.g. "2025-12-01T10:00:00")
    """
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
def execute_project_plan(goal: str, tasks: str, budget: float = 0):
    """Generates a multi-step plan. Tasks must be a JSON string. Budget is the max limit in dollars."""
    global pending_plan, current_budget_warning
    try:
        print(f"🧐 DEBUG RAW AI INPUT: {tasks}")
        raw_data = json.loads(tasks)
        if isinstance(raw_data, dict) and "tasks" in raw_data:
            raw_data = raw_data["tasks"]
        if not isinstance(raw_data, list):
            return "Error: AI returned invalid JSON structure."

        clean_tasks = []
        total_project_cost = 0

        target_budget = budget

        for t in raw_data:
            if isinstance(t, str):
                t = {"name": t, "desc": "Auto-generated task", "owner": "Unassigned"}
            # ensure name exists
            if "name" not in t:
                t["name"] = t.get("task_name") or t.get("title") or t.get("action") or t.get("task") or "Task"
            name = t.get("name")
            desc = t.get("desc") or t.get("description") or ""
            owner = t.get("owner") or t.get("assignee") or "Unassigned"

            if owner == "Unassigned" or not owner:
                owner = auto_assign_owner(name, desc)
            if owner == "Unassigned":
                owner = get_default_owner()
            # --- COST CALCULATION ---
            # A. Time Est
            days = 2
            for k, v in DURATION_RULES.items():
                if k in name.lower(): days = max(days, v)
            
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
            desc = f"{desc}\n\n{cost_details}\n⏱ Est: {days} days @ ${emp_rate}/hr"
            
            clean_tasks.append({"name": name, "desc": desc, "owner": owner})

        # --- RISK ANALYSIS ---
        # Default styling (No budget limit set)
        budget_status_msg = f"💵 **Total Project Cost:** ${total_project_cost}"
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
        # 1. Fetch Trello Cards
        risks = []
        try:
            response = requests.get(N8N_GET_CARDS_URL, timeout=10)
            if response.status_code == 200:
                cards = response.json()
                today = datetime.now()
                for c in cards:
                    if isinstance(c, dict) and "json" in c: c = c["json"]
                    if c.get("due"):
                        try:
                            d = datetime.fromisoformat(c["due"].replace("Z", "+00:00")).replace(tzinfo=None)
                            # ✅ FIX: Check if date is today or past (>= instead of >)
                            if today.date() >= d.date():
                                risks.append(f"⚠️ DUE/OVERDUE: '{c['name']}'")
                        except: pass
        except Exception as e:
            print(f"⚠️ Trello Check Failed: {e}")

        # 2. ADD BUDGET RISK (Priority #1)
        if current_budget_warning:
            risks.insert(0, current_budget_warning)

        # 3. Save to Global Variable
        current_risks = risks
        
        if not risks:
            return "✅ ALL GOOD. No overdue tasks or budget issues."
        
        return "Risks Found"
    except Exception as e:
        return f"Error: {e}"

# Bind tools
llm_with_tools = llm.bind_tools([create_task_in_trello, send_slack_announcement, consult_project_memory, execute_project_plan, check_project_status, schedule_meeting_tool])

# --------------------
# ENDPOINTS
# --------------------
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
def chat_endpoint(req: UserRequest):
    chat_history.append(HumanMessage(content=req.message))
    response = llm_with_tools.invoke(chat_history)
    final = response.content
    approval = False
    plan_staged = False

    if response.tool_calls:
        # First handle any plan calls first (so we stage instead of creating)
        for tc in response.tool_calls:
            if tc["name"] == "execute_project_plan":
                res = execute_project_plan.invoke(tc["args"])
                if res == "PLAN_STAGED":
                    plan_staged = True
                    if pending_plan:
                        # 1. Format Tasks
                        preview_lines = [f"• {t.get('name')} → {t.get('owner')}" for t in pending_plan["tasks"]]
                        
                        # 2. Get the Pre-Formatted Budget Info
                        budget_info = pending_plan.get("budget_summary", "")

                        # 3. Construct the Message
                        final = (
                            f"I have drafted a plan:\n"
                            f"{budget_info}\n\n"  # <--- This will now be 🚨 or ✅ automatically
                            f"{chr(10).join(preview_lines)}\n\n"
                            f"Proceed?"
                        )
                        approval = True
                    else:
                        final = "Plan generated. Proceed?"
                        approval = True
                else:
                    final = res
                break

        # If not staging a plan, run other tools
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
                    # handle nested plan from memory
                    if follow.tool_calls:
                        for tc_follow in follow.tool_calls:
                            if tc_follow["name"] == "execute_project_plan":
                                execute_project_plan.invoke(tc_follow["args"])
                                if pending_plan:
                                    preview = "\n".join([f"• {t['name']} → {t['owner']}" for t in pending_plan["tasks"]])
                                    final = f"Based on our records, I drafted a plan:\n\n{preview}\n\nProceed?"
                                    approval = True

    chat_history.append(response)
    return {"reply": final, "approval_required": approval}

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
        success, cal_msg = internal_create_trello(name, desc, owner, start_hour=current_hour)
        status_text = f"Created: {name}"
        if cal_msg:
            status_text += " (+Calendar)"
        results.append(status_text)
        current_hour += 2
        if current_hour > 17:
            current_hour = 9
    try:
        requests.post(N8N_SLACK_URL, json={"message": f"✅ APPROVED: {pending_plan['goal']}\n" + "\n".join(results)}, timeout=5)
    except:
        pass
    pending_plan = None
    return {"status": "Executed", "details": "\n".join(results)}

@app.post("/reject")
def reject_plan():
    global pending_plan
    pending_plan = None
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
