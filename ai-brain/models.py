from pydantic import BaseModel
from typing import List, Optional

# ==========================================
# 🔐 RBAC — ROLES
# ==========================================
# Roles: "admin", "pm", "developer"
# - admin: Full access, can manage users and system settings
# - pm: Can approve plans, manage team, view all reports
# - developer: Can log time, view their tasks, update task status

VALID_ROLES = ["admin", "pm", "developer"]

# --- USER & AUTH ---
class User(BaseModel):
    username: str
    password: str
    role: str = "developer"  # Default role for new users

class ProfileUpdate(BaseModel):
    display_name: str
    email: str

# --- EMPLOYEE ---
class Employee(BaseModel):
    name: str
    role: str
    skills: List[str]
    email: str
    trello_id: Optional[str] = ""
    rate: int = 50

# --- CHAT & APPROVAL ---
class ApproveRequest(BaseModel):
    session_id: str  

class RejectRequest(BaseModel):
    reason: str = "No reason provided."
    session_id: str 

class UserRequest(BaseModel):
    message: str
    session_id: str = "default_session"
    project_id: Optional[str] = None  # Multi-project support

# --- TIME TRACKING ---
class TimeLogRequest(BaseModel):
    task_name: str
    hours: float
    note: str = ""

class TimeLogEntry(BaseModel):
    task_name: str
    logged_by: str
    hours: float
    note: str = ""

# ==========================================
# 📦 EPIC → STORY → TASK HIERARCHY
# ==========================================

class EpicCreate(BaseModel):
    name: str
    description: str = ""
    project_id: str = "default"
    color: str = "#6C5DD3"  # For Gantt chart bar coloring

class EpicUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # "active", "completed", "archived"
    color: Optional[str] = None

class StoryCreate(BaseModel):
    name: str
    description: str = ""
    epic_id: str = ""
    story_points: int = 0
    assigned_to: str = "Unassigned"

class StoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # "todo", "in_progress", "done"
    story_points: Optional[int] = None
    assigned_to: Optional[str] = None

class TaskItemCreate(BaseModel):
    name: str
    description: str = ""
    story_id: str = ""
    epic_id: str = ""
    sprint_id: str = ""
    assigned_to: str = "Unassigned"
    status: str = "todo"  # "todo", "in_progress", "done"
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    estimated_hours: float = 0
    depends_on: List[str] = []  # list of task IDs

class TaskItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sprint_id: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    depends_on: Optional[List[str]] = None

# --- SPRINT MANAGEMENT ---
class SprintCreate(BaseModel):
    name: str
    goal: str = ""
    start_date: str
    end_date: str
    capacity_hours: float = 0
    project_id: str = "default"

class SprintUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    capacity_hours: Optional[float] = None
    status: Optional[str] = None  # "planning", "active", "completed"

# --- MULTI-PROJECT ---
class ProjectCreate(BaseModel):
    name: str
    trello_board_url: str = ""
    n8n_trello_webhook: str = ""
    n8n_get_cards_url: str = ""
    n8n_slack_webhook: str = ""

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    trello_board_url: Optional[str] = None
    n8n_trello_webhook: Optional[str] = None
    n8n_get_cards_url: Optional[str] = None
    n8n_slack_webhook: Optional[str] = None

# --- DASHBOARD CHARTS ---
class ChartDataSet(BaseModel):
    label: str
    data: List[int]
    borderColor: Optional[str] = None
    backgroundColor: Optional[List[str]] = None

class ChartData(BaseModel):
    labels: List[str]
    datasets: List[ChartDataSet]

class FinanceItem(BaseModel):
    date: str
    category: str
    details: str
    amount: str
    status: str
    isPositive: bool
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None

class WorkloadItem(BaseModel):
    name: str
    role: str
    active_tasks: int
    status: str  # "available", "busy", "overloaded"

class DashboardStats(BaseModel):
    tasks_due: int
    overdue: int
    active: int
    resolved_risks: int
    in_progress: int
    not_started: int
    total_team: int
    total_budget: str        
    current_project: str     
    recent_projects: List[str] 
    line_chart: ChartData
    donut_chart: ChartData
    finance_table: List[FinanceItem]
    user_display_name: Optional[str] = "Project Manager"
    team_workload: Optional[List[WorkloadItem]] = []
    user_role: Optional[str] = "developer"  # For RBAC-aware UI

# ==========================================
# 📋 MEETING-TO-TASKS PIPELINE
# ==========================================

class MeetingActionItem(BaseModel):
    task: str
    owner: str = "Unassigned"
    deadline: str = ""

class MeetingRecord(BaseModel):
    filename: str
    uploaded_by: str
    summary: str = ""
    key_decisions: List[str] = []
    action_items: List[MeetingActionItem] = []
    cards_created: int = 0
    created_at: Optional[str] = None

# ==========================================
# ⚠️ RISK PREDICTION (PRE-MORTEM AI)
# ==========================================

RISK_CATEGORIES = ["schedule", "resource", "budget", "technical", "dependency", "scope"]

class RiskItem(BaseModel):
    title: str
    description: str = ""
    category: str = "schedule"  # One of RISK_CATEGORIES
    probability: int = 1        # 1-5
    impact: int = 1             # 1-5
    risk_score: int = 1         # probability * impact (auto-calculated)
    status: str = "open"        # "open", "mitigated", "closed"
    mitigation: str = ""
    detected_at: Optional[str] = None
    project_id: str = "default"

class RiskUpdate(BaseModel):
    status: Optional[str] = None       # "open", "mitigated", "closed"
    mitigation: Optional[str] = None
    probability: Optional[int] = None
    impact: Optional[int] = None

