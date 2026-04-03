from pydantic import BaseModel
from typing import List, Optional

# --- EMPLOYEE & USER ---
class Employee(BaseModel):
    name: str
    role: str
    skills: List[str]
    email: str
    trello_id: Optional[str] = ""
    rate: int = 50

class ProfileUpdate(BaseModel):
    display_name: str
    email: str

class User(BaseModel):
    username: str
    password: str

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
