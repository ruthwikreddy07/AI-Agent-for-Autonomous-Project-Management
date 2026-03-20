<p align="center">
  <img src="https://img.shields.io/badge/Angular-20-DD0031?style=for-the-badge&logo=angular&logoColor=white" alt="Angular 20" />
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB" />
  <img src="https://img.shields.io/badge/AI-Groq%20%7C%20Gemini-blueviolet?style=for-the-badge&logo=google&logoColor=white" alt="Groq | Gemini" />
  <img src="https://img.shields.io/badge/n8n-8%20Workflows-EA4B71?style=for-the-badge&logo=n8n&logoColor=white" alt="n8n 8 Workflows" />
  <img src="https://img.shields.io/badge/Pinecone-Vector%20DB-00C7B7?style=for-the-badge&logo=pinecone&logoColor=white" alt="Pinecone" />
  <img src="https://img.shields.io/badge/GitHub-Sync-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Sync" />
</p>

<h1 align="center">🤖 Autonomous AI Project Manager</h1>

<p align="center">
  <strong>An intelligent, tool-driven AI agent that autonomously reasons, plans, and executes project management workflows — powered by Groq LLMs (Llama 3.1 / 3.3), Gemini Embeddings, and Pinecone Vector Memory.</strong>
</p>

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-user-flow--available-tasks">User Flow</a> •
  <a href="#-technology-stack">Tech Stack</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-key-features">Features</a> •
  <a href="#-project-structure">Structure</a> •
  <a href="#-getting-started">Getting Started</a> •
  <a href="#-api-reference">API</a> •
  <a href="#-deployment">Deployment</a> •
  <a href="#-roadmap">Roadmap</a>
</p>

---

## 📌 Overview

<<<<<<< HEAD
Traditional project management suffers from fragmented tooling, manual coordination, poor skill-based task allocation, budget overruns, and no proactive risk detection. Managers constantly track dependencies, deadlines, and costs manually — leading to persistent inefficiencies.
=======
## 🔎 Problem It Overcomes
>>>>>>> d800925 (Made documentation Changes)

**This project solves that** by introducing an **Autonomous AI Project Management Agent** that converts high-level goals into structured execution plans, monitors progress in real time, and self-heals when things go off track — all while keeping humans in control of critical decisions.

### Why This Project Stands Out

| | |
| :---: | :--- |
| 🧠 | **Autonomous AI Agent Architecture** — LangChain tool-binding with 7 specialized tools for end-to-end project orchestration |
| 🔗 | **Real-World Integrations** — Trello (task tracking), Slack (alerts), Google Calendar (scheduling), all wired through n8n middleware |
| 🔁 | **Self-Healing Scheduling** — Automatically detects overdue tasks, reschedules them to the next business day, and cascades date changes to dependent tasks |
| 💰 | **Cost-Aware Planning** — Budget estimation using employee hourly rates, tool costs, and real-time burn rate analysis |
| 🔐 | **Production-Ready** — JWT authentication, session-based chat memory, CORS-hardened FastAPI backend, and Angular 20 SSR frontend |

---

## 🧠 How It Works

```mermaid
graph TD
    classDef step fill:#cce5ff,stroke:#007bff,stroke-width:2px,color:#333;
    classDef action fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#333;

    A["1. User enters a high-level goal\ne.g. Build a mobile app"]:::step
    B["2. AI decomposes goal into structured tasks\nwith dependencies and cost estimates"]:::step
    C["3. Tasks are auto-assigned by skill,\ntime-estimated, and budget-calculated"]:::step
    D["4. Manager reviews and approves the plan"]:::step
    E["5. AI executes the approved plan"]:::step
    F["Creates Trello Cards\nwith labels and assignees"]:::action
    G["Schedules Focus Time\nin Google Calendar"]:::action
    H["Sends Slack Notifications\nvia n8n webhooks"]:::action
    I["Tracks Progress and\nauto-heals delays"]:::action

    A --> B --> C --> D --> E
    E --> F
    E --> G
    E --> H
    E --> I
```

---

## 🗺 User Flow & Available Tasks

The diagram below maps every action a user or manager can take, and how the AI backend transitions from intent to physical execution across external tools.

```mermaid
graph TD
    classDef userAction fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#333;
    classDef aiSystem fill:#cce5ff,stroke:#007bff,stroke-width:2px,color:#333;
    classDef external fill:#fff3cd,stroke:#ffc107,stroke-width:2px,color:#333;

    User(["User / Project Manager"])

    subgraph User_Capabilities ["User Capabilities"]
        A["Enter High-Level Goal in Chat"]:::userAction
        B["Upload Project Documents"]:::userAction
        C["Ask Questions About Project Context"]:::userAction
        D["Review and Approve / Reject Plan"]:::userAction
        E["View Dashboard and Burn Analysis"]:::userAction
        F["Trigger Risk Evaluation"]:::userAction
        G["Manage Team / Employees"]:::userAction
        H["Schedule Meetings"]:::userAction
        I["Send Slack Announcements"]:::userAction
        Z["Login / Register / Update Profile"]:::userAction
    end

    User --> A
    User --> B
    User --> C
    User --> D
    User --> E
    User --> F
    User --> G
    User --> H
    User --> I
    User --> Z

    subgraph AI_Processing ["AI Processing and RAG Memory"]
        API["FastAPI Backend\n(server.py)"]:::aiSystem
        Agent["Groq LLM + LangChain\n7 Bound Tools"]:::aiSystem
        Standup["Daily Standup Report\nvia n8n Cron"]:::aiSystem
        RAG["Pinecone Vector DB\nDocument Context"]:::aiSystem

        API <-->|"Intent Resolution\nand Tool Execution"| Agent
        Agent <-->|"Retrieve Document Context"| RAG
        B -->|"Autonomous Ingestion\nand Vectorization"| RAG
        A --> API
        C --> API
        H --> API
        I --> API
        E -->|"Fetch Trello Baselines\nand Cost Data"| API
        F -->|"Force Schedule Check"| API
    end

    subgraph Planning_Engine ["Planning Engine"]
        Plan["Task Breakdown with\nTopological Sorting"]:::aiSystem
        Timeline["Smart Timeline\nSkips Weekends and Holidays"]:::aiSystem
        Budget["Budget Estimation\nPersonnel + Tool Costs"]:::aiSystem
        Assign["Skill-Based Auto-Assignment\nfrom MongoDB Roster"]:::aiSystem
        Agent --> Plan
        Plan --> Timeline
        Timeline --> Budget
        Budget --> Assign
        Assign --> D
    end

    subgraph Execution_Phase ["Execution Phase"]
        Exec["Execute Approved Plan"]:::aiSystem
        D -->|"One-click Approve or Reject"| API
        API --> Exec
    end

    subgraph Integrations ["Integrations and Automations"]
        Trello["Trello\nCreate Cards, Labels, Assign Members"]:::external
        GCal["Google Calendar\nBook Meetings and Focus Time"]:::external
        n8n["n8n Middleware\n8 Active Workflows"]:::external
        Slack["Slack\nAnnouncements and Standup Reports"]:::external
        Gmail["Gmail\nUrgent Task Email Alerts"]:::external
        GitHub["GitHub\nPush Webhook Trigger"]:::external

        Exec -->|"Create via n8n webhook"| Trello
        Exec -->|"Book Focus Time blocks"| GCal
        Exec -->|"Webhook Triggers"| n8n
        n8n --> Slack
        n8n --> Gmail

        API -->|"Self-healing Schedule\nDirect Trello API"| Trello
        API -->|"Check Availability and\nAuto-reschedule"| GCal
        GitHub -->|"Push events with\nStarted/Fixed #ID"| n8n
        n8n -->|"Auto-move cards\nbetween lists"| Trello
        Standup -->|"Cron 9 AM daily"| n8n
    end
```

---

## 🛠 Technology Stack

### Backend

| Technology | File(s) | Purpose |
| :--- | :--- | :--- |
| **Python + FastAPI** | `server.py` | REST API server, request handling, and all core business logic (1800+ lines) |
| **JWT + Passlib (Bcrypt)** | `server.py` | Secure token-based authentication and password hashing |
| **MongoDB (PyMongo)** | `server.py`, `create_admin.py` | Stores users, employees (skills, roles, hourly rates), and session-based chat history |

### AI & Machine Learning

| Technology | File(s) | Purpose |
| :--- | :--- | :--- |
| **Groq API (Llama 3.1-8b-instant)** | `server.py` | Primary high-speed LLM for reasoning, planning, and tool invocation |
| **Groq API (Llama 3.3-70b-versatile)** | `agent.py` | Standalone CLI agent prototype for testing tool calls |
| **LangChain** | `server.py` | Tool orchestration — binds 7 tools to the LLM, manages multi-turn context |
| **Google Gemini (gemini-embedding-001)** | `server.py` | Remote text-to-vector embeddings for the RAG memory pipeline |
| **SentenceTransformers (all-MiniLM-L6-v2)** | `ingest.py` | Local embedding generation for the standalone document ingestion script |
| **Pinecone** | `server.py`, `ingest.py` | Vector database for long-term project memory (RAG retrieval) |

### Integrations

| Technology | File(s) | Purpose |
| :--- | :--- | :--- |
| **n8n (8 active workflows)** | `server.py` | Workflow automation middleware — bridges Trello, Slack, Gmail, GitHub, and dashboard analytics |
| **Trello API** | `server.py` | Task card creation (via n8n), label assignment, member mapping, and schedule healing (direct API) |
| **Google Calendar API** | `calendar_tool.py` | Availability checking, free-slot discovery, meeting booking with Google Meet links, and focus time scheduling |
| **Slack** | `server.py` | Team announcements, meeting notifications, daily standup reports, and urgent alerts — all via n8n |
| **Gmail (via n8n)** | `server.py` | Urgent task email dispatch triggered through the `N8N_ALERT_URL` webhook using Gmail OAuth |
| **GitHub (via n8n)** | n8n workflow | Push webhook listener — auto-moves Trello cards when commits reference `Started #ID` or `Fixed #ID` |

### Frontend

| Technology | File(s) | Purpose |
| :--- | :--- | :--- |
| **Angular 20 (SSR)** | `frontend-dashboard/` | Full interactive dashboard with 5 page components: Login, Dashboard, Chat, Team, Settings |
| **Chart.js** | `dashboard/` | Line charts (task timeline) and donut charts (task status distribution) on the dashboard |

---

## 🏗 System Architecture

```mermaid
graph TB
    classDef frontend fill:#E44D26,stroke:#fff,stroke-width:2px,color:#fff;
    classDef backend fill:#4B8BBE,stroke:#FFE873,stroke-width:2px,color:#fff;
    classDef ai fill:#8A2BE2,stroke:#fff,stroke-width:2px,color:#fff;
    classDef db fill:#4EA94B,stroke:#fff,stroke-width:2px,color:#fff;
    classDef external fill:#0079BF,stroke:#fff,stroke-width:2px,color:#fff;
    classDef middleware fill:#EA4B71,stroke:#fff,stroke-width:2px,color:#fff;

    subgraph Frontend_Layer ["Frontend Layer"]
        UI["Angular 20 SSR Dashboard\n(Login, Dashboard, Chat, Team, Settings)"]:::frontend
        Charts["Chart.js\n(Line + Donut Charts)"]:::frontend
    end

    subgraph Backend_Layer ["AI Brain - Core Backend"]
        API["FastAPI REST API\n(JWT Auth, CORS, 17 Endpoints)"]:::backend
        Tools["LangChain Tool Orchestrator\n(7 Bound Tools)"]:::backend
        Processor["Unified Tool Processor\n(Multi-turn Execution Loop)"]:::backend
        Planner["Planning Engine\n(Topological Sort, Smart Timeline,\nBudget Estimation)"]:::backend
        Healer["Self-Healing Engine\n(Overdue Detection,\nDependency Cascade)"]:::backend
        Upload["Document Upload Pipeline\n(Chunking + Vectorization)"]:::backend
    end

    subgraph AI_Layer ["AI and Embedding Models"]
        Groq["Groq API\n(Llama 3.1-8b-instant)"]:::ai
        Groq70b["Groq API\n(Llama 3.3-70b-versatile)\nCLI Agent"]:::ai
        Gemini["Google Gemini\n(gemini-embedding-001)"]:::ai
        MiniLM["SentenceTransformers\n(all-MiniLM-L6-v2)\nLocal Ingestion"]:::ai
    end

    subgraph DB_Layer ["Database Layer"]
        Mongo[("MongoDB Atlas\n(Users, Employees,\nChat History)")]:::db
        Pinecone[("Pinecone Vector DB\n(Project Memory /\nRAG Knowledge)")]:::db
    end

    subgraph Middleware_Layer ["n8n Automation Layer (8 Active Workflows)"]
        n8n_card["WF1: Creating a Card Trello"]:::middleware
        n8n_slack["WF2: Send Message to Slack"]:::middleware
        n8n_cards["WF3: Get Cards"]:::middleware
        n8n_alert["WF4: Emergency Alerts (Gmail)"]:::middleware
        n8n_all["WF5: Get Backlog and Doing Cards"]:::middleware
        n8n_dash["WF6: Dashboard Data Aggregator"]:::middleware
        n8n_standup["WF7: Daily Standup (Cron 9AM)"]:::middleware
        n8n_github["WF8: GitHub Sync"]:::middleware
    end

    subgraph External_Layer ["External Systems"]
        Trello["Trello\n(Cards, Labels, Members,\nDue Dates)"]:::external
        Slack["Slack\n(Announcements,\nStandup Reports)"]:::external
        GCal["Google Calendar\n(Meetings, Focus Time,\nGoogle Meet Links)"]:::external
        Gmail["Gmail\n(Urgent Task Emails)"]:::external
        GitHub["GitHub\n(Push Webhooks)"]:::external
    end

    UI <-->|"HTTP + JWT Bearer"| API
    Charts -.->|"Renders data from"| API

    API <-->|"Auth, Employees, Chat"| Mongo
    API <-->|"Vector Retrieval"| Pinecone
    Upload -->|"Chunk + Embed + Upsert"| Pinecone

    API <-->|"Conversation Loop"| Tools
    Tools <-->|"Multi-turn Reasoning"| Processor
    Tools <-->|"LLM Inference"| Groq
    Processor -->|"Plan Staging"| Planner
    Processor -->|"Schedule Fix"| Healer

    API -->|"Embed text"| Gemini
    Gemini -->|"3072-dim vectors"| Pinecone
    MiniLM -->|"384-dim vectors"| Pinecone

    API <-->|"Direct API:\nUpdate due dates"| Trello
    API <-->|"Booking + Availability"| GCal

    API -->|"Task payload"| n8n_card
    API -->|"Message payload"| n8n_slack
    API -->|"Fetch cards"| n8n_cards
    API -->|"Urgent alert"| n8n_alert
    API -->|"All cards fetch"| n8n_all
    API -->|"Dashboard data"| n8n_dash

    n8n_card -->|"Create labelled cards"| Trello
    n8n_slack -->|"Post to channel"| Slack
    n8n_cards -->|"Return card data"| API
    n8n_alert -->|"Send urgent email"| Gmail
    n8n_all -->|"Return aggregated data"| API
    n8n_dash -->|"Return analytics"| API

    n8n_standup -->|"Read Done, Doing,\nBacklog columns"| Trello
    n8n_standup -->|"Post standup report"| Slack

    GitHub -->|"Push events"| n8n_github
    n8n_github -->|"Move cards:\nStarted to Doing,\nFixed to Done"| Trello

    Healer -->|"Reschedule overdue +\ncascade dependencies"| Trello
```

---

## ⭐ Key Features

### 1. Intelligent Project Planning (`execute_project_plan`)
- Decomposes high-level goals into a structured, ordered list of tasks with descriptions and owners
- Resolves task dependencies using **topological sorting** with fuzzy name matching
- Generates smart timelines that **skip weekends and company holidays** automatically
- Applies **sequential fallback**: if the AI returns zero dependencies, the system chains tasks in order
- Estimates per-task cost using `days × 8 hours × employee hourly rate + tool costs`
- Warns on budget overruns with red/green status indicators

### 2. Skill-Based Auto-Assignment (`auto_assign_owner`)
- **Strategy 1 — Exact Skill Match**: Scans MongoDB employee roster and matches task keywords against declared skills
- **Strategy 2 — Role Keyword Match**: Falls back to matching common role keywords (frontend, backend, QA, DevOps, etc.)
- Automatically resolves Trello member IDs from employee emails for card assignment
- Books a **Focus Time block** in the assignee's Google Calendar upon task creation

### 3. Self-Healing Schedule (`heal_project_schedule`)
- **Phase 1**: Scans all Trello cards for overdue or due-today tasks; reschedules them to the next valid business day (respecting 9 AM–6 PM working hours)
- **Phase 2**: Detects dependency chains via `Blocked By` annotations in card descriptions; pushes dependent tasks forward if their blocker was delayed
- Updates the Trello board directly via the Trello REST API
- Sends proactive alerts via Slack and email for urgent tasks

### 4. RAG-Powered Project Memory (`consult_project_memory`)
- Accepts uploaded project documents through the `/upload` endpoint
- Chunks documents into 1000-character segments and embeds them using **Gemini (gemini-embedding-001)**
- Tags all vectors with the authenticated `username` for per-user data isolation
- Retrieves the top 3 most relevant chunks from Pinecone when users query project context

### 5. Calendar & Meeting Management (`schedule_meeting_tool`)
- **Two-step flow**: `action="check"` verifies availability → `action="book"` creates the event
- If the requested slot is busy, automatically scans up to 8 hours ahead (within 9 AM–6 PM) to find the next free slot
- Creates Google Calendar events with **Google Meet video links** for meetings
- Creates non-meeting **Focus Time** blocks for task assignees (no Meet link)
- Automatically notifies Slack after booking

### 6. Human-in-the-Loop Safety
- All AI-generated plans require **explicit manager approval** via the `/approve` endpoint before execution
- Managers can **reject plans** via `/reject` with a reason, which clears the staged plan and persists the rejection to chat history
- The AI never executes high-risk or irreversible actions without validation
- All decisions are transparent — task previews include cost breakdowns, timelines, and assignee details

### 7. Daily Standup Report (n8n Cron Workflow)
- **Fully automated** n8n workflow triggered daily at **9:00 AM** via cron schedule
- Reads all cards from Trello's **Done**, **Doing**, and **Backlog** columns
- Formats a structured standup report with ✅ Completed / 🚧 In Progress / 📌 Up Next sections
- Posts the formatted report directly to the **#project-updates** Slack channel
- Zero manual intervention required — runs autonomously every weekday

### 8. GitHub Sync (n8n GitHub Webhook Workflow)
- Listens for **GitHub push webhook events** on the connected repository
- Parses commit messages for keywords: `Started #<card_number>` or `Fixed #<card_number>`
- **`Started #42`** → Automatically moves Trello card #42 from **Backlog** → **Doing**
- **`Fixed #42`** → Automatically moves Trello card #42 from **Doing** → **Done**
- Resolves Trello card IDs by querying the board's `idShort` field against the referenced number
- Eliminates the need for manual Trello status updates when developers commit code

### 9. Advanced Operational Capabilities

| Capability | Implementation |
| :--- | :--- |
| 🔐 **JWT-Secured API** | All endpoints (except `/token`, `/register`, `/`) require Bearer token authentication |
| 💬 **Session-Based Chat Memory** | Chat messages are persisted in MongoDB per `session_id` with timestamp ordering |
| 🔁 **Fault-Tolerant Execution** | Trello card creation retries up to 3 times with 2-second backoff; n8n workflow count retries up to 3 times with increasing timeouts (15s/30s/45s) |
| 🧠 **Dynamic System Prompt** | System prompt is refreshed with the live team roster and today's date on every invocation |
| 📊 **Financial Burn Analysis** | Dashboard aggregates cost data from Trello card descriptions, showing the top 5 high-impact budget items |
| 🚨 **Urgent Alert System** | Tasks containing "critical", "urgent", "crash", or "alert" trigger Gmail dispatch to the assignee via the `N8N_ALERT_URL` webhook |
| 🤖 **n8n Active Workflow Counter** | Dashboard header dynamically shows the count of 8 active n8n automation workflows |
| 📈 **Real-Time Dashboard** | Line charts (completed/active/upcoming tasks over 14 days), donut charts (task status distribution), and finance tables — all sourced from live Trello data |
| 💬 **Slack Auto-Notifications** | Every task creation, meeting booking, and plan approval automatically posts a formatted message to the team Slack channel via n8n |
| 🔄 **Anti-Flood Protection** | 2-second delays between Slack messages and 5-second delays between Trello card creation during batch plan execution to prevent API rate limiting |

---

## 📁 Project Structure

```text
ai-agent-manager/
├── ai-brain/                              # Python / FastAPI Backend
│   ├── server.py                          # Core application — 17 API endpoints, 7 LangChain tools,
│   │                                      #   planning engine, self-healing, dashboard analytics
│   ├── agent.py                           # Standalone CLI agent prototype (Llama 3.3-70b)
│   ├── calendar_tool.py                   # Google Calendar API — availability, booking, Meet links
│   ├── ingest.py                          # Standalone document ingestion with SentenceTransformers
│   ├── create_admin.py                    # Utility script to seed an admin user in MongoDB
│   ├── credentials.json                   # Google OAuth2 client credentials (Calendar API)
│   ├── token.json                         # Google OAuth2 refresh token (auto-generated)
│   ├── project_info.txt                   # Sample project knowledge base for ingestion
│   ├── requirements.txt                   # Python dependencies
│   └── .env                               # Environment variables (API keys, webhook URLs)
│
├── frontend-dashboard/                    # Angular 20 SSR Frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── ai.service.ts              # HTTP service — all API calls + mock mode toggle
│   │   │   ├── app.ts                     # Root component with sidebar navigation
│   │   │   ├── app.routes.ts              # Route definitions (5 pages)
│   │   │   ├── app.css                    # Global application styles
│   │   │   ├── login/                     # Authentication page (login + register)
│   │   │   ├── dashboard/                 # Main dashboard — charts, stats, finance table
│   │   │   ├── chat/                      # AI chat interface with approve/reject controls
│   │   │   ├── team/                      # Employee management (add/edit/delete)
│   │   │   ├── settings/                  # User profile settings
│   │   │   └── tasks/                     # Task view component
│   │   ├── environments/                  # Environment configs (dev/prod API URLs)
│   │   ├── server.ts                      # Express SSR server
│   │   └── index.html                     # Root HTML template
│   ├── angular.json                       # Angular project configuration
│   └── package.json                       # Node.js dependencies (Angular 20, Chart.js)
│
└── n8n-workflows/                         # n8n Automation Configuration
    └── .env                               # n8n basic auth credentials
```

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+ and npm
- **MongoDB** instance (Atlas or local)
- **Pinecone** account and API key (index name: `project-memory`)
- **Groq** API key
- **Google Cloud** project with the Calendar API enabled + OAuth2 credentials
- **n8n** instance (self-hosted or cloud) with webhook workflows configured
- **Trello** API key and token

---

### 1. Clone the Repository

```bash
git clone https://github.com/ruthwikreddy07/AI-Agent-for-Autonomous-Project-Management.git
cd AI-Agent-for-Autonomous-Project-Management
```

### 2. Backend Setup

```bash
cd ai-brain

# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the `ai-brain/` directory:

```env
# AI Keys
GROQ_API_KEY=your_groq_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_HOST=https://your-index.svc.pinecone.io
GOOGLE_API_KEY=your_google_gemini_api_key
HF_TOKEN=your_huggingface_token

# Database & Security
MONGO_URI=your_mongodb_connection_string
SECRET_KEY=your_jwt_secret_key

# Trello Direct API (for self-healing)
TRELLO_API_KEY=your_trello_api_key
TRELLO_TOKEN=your_trello_token
PASTE_RED_LABEL_ID=your_red_label_id
PASTE_GREEN_LABEL_ID=your_green_label_id
PASTE_YELLOW_LABEL_ID=your_yellow_label_id

# n8n Webhook URLs (6 webhook-triggered endpoints)
N8N_TRELLO_URL=https://your-n8n/webhook/test-connection
N8N_SLACK_URL=https://your-n8n/webhook/send-slack
N8N_GET_CARDS_URL=https://your-n8n/webhook/get-cards-v2
N8N_ALERT_URL=https://your-n8n/webhook/send-alert
N8N_GET_ALL_CARDS_URL=https://your-n8n/webhook/get-all-cards-in-backlog-and-doing
N8N_DASHBOARD_URL=https://your-n8n/webhook/get-dashboard-analytics

# n8n API (for active workflow count on dashboard)
N8N_API_KEY=your_n8n_api_key
N8N_BASE_URL=https://your-n8n/api/v1
```

```bash
# (Optional) Ingest sample project knowledge into Pinecone
python ingest.py

# Start the backend server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### 3. Frontend Setup

```bash
cd frontend-dashboard

# Install dependencies
npm install

# Start the development server
ng serve
```

The frontend will be available at `http://localhost:4200`.

### 4. n8n Workflow Setup

1. Deploy or log in to your n8n instance.
2. Configure the following **8 active workflows**:

| # | Workflow Name | Trigger | Description |
| :---: | :--- | :--- | :--- |
| 1 | **Creating a Card Trello** | Webhook (`/test-connection`) | Receives task payload from backend, creates a labelled Trello card with assignee and due date |
| 2 | **Send Message to Slack** | Webhook (`/send-slack`) | Receives message payload, posts formatted text to the `#project-updates` Slack channel |
| 3 | **Get Cards** | Webhook (`/get-cards-v2`) | Returns all cards from the Backlog list for project status checks |
| 4 | **Emergency Alerts** | Webhook (`/send-alert`) | Receives task + email payload, dispatches urgent Gmail to the assigned team member |
| 5 | **Get Backlog and Doing Cards** | Webhook (`/get-all-cards-in-backlog-and-doing`) | Fetches cards from Backlog + Doing lists, merges and aggregates, returns combined data |
| 6 | **Dashboard Data Aggregator** | Webhook (`/get-dashboard-analytics`) | Fetches cards from all 3 lists (Backlog, Doing, Done), merges for dashboard analytics |
| 7 | **Daily Standup** | Cron (9:00 AM daily) | Reads Done/Doing/Backlog columns, formats standup report, posts to Slack automatically |
| 8 | **GitHub Sync** | GitHub Push Webhook | Parses commit messages for `Started #ID` / `Fixed #ID`, auto-moves corresponding Trello cards |

3. Update the webhook URLs in the backend `.env` file.
4. Connect the **GitHub Sync** workflow to your repository via GitHub OAuth.
5. Connect the **Emergency Alerts** workflow to your Gmail account via Gmail OAuth.

---

## 📡 API Reference

All endpoints except `/token`, `/register`, and `/` require a **JWT Bearer token** in the `Authorization` header.

### Authentication

| Endpoint | Method | Auth | Description |
| :--- | :---: | :---: | :--- |
| `/token` | `POST` | — | Login with username/password (OAuth2 form), returns JWT |
| `/register` | `POST` | — | Create a new user account |

### Core AI

| Endpoint | Method | Auth | Description |
| :--- | :---: | :---: | :--- |
| `/chat` | `POST` | JWT | Main conversational loop — intent resolution, tool execution, multi-turn reasoning |
| `/chat/history/{session_id}` | `GET` | — | Returns full chat history for a session (chronological order) |
| `/upload` | `POST` | JWT | Upload a document — chunks, embeds via Gemini, upserts to Pinecone, triggers autonomous AI analysis |
| `/approve` | `POST` | JWT | Executes a staged plan — creates Trello cards, books calendar events, sends Slack notifications |
| `/reject` | `POST` | — | Rejects a staged plan with a reason, clears internal state, persists rejection to chat |

### Dashboard & Monitoring

| Endpoint | Method | Auth | Description |
| :--- | :---: | :---: | :--- |
| `/dashboard/data` | `GET` | JWT | Full dashboard payload — task counts, chart data, finance burn table, active n8n workflows, project sidebar |
| `/risks` | `GET` | — | Force-refreshes the project schedule check and returns all active risk items |
| `/` | `GET` | — | Health check — returns database connection and key configuration status |

### Team Management

| Endpoint | Method | Auth | Description |
| :--- | :---: | :---: | :--- |
| `/employees` | `GET` | — | List all employees |
| `/employees` | `POST` | — | Add an employee (auto-resolves Trello member ID from email) |
| `/employees/{email}` | `PUT` | — | Update an employee record |
| `/employees/{email}` | `DELETE` | — | Delete an employee |

### User Profile

| Endpoint | Method | Auth | Description |
| :--- | :---: | :---: | :--- |
| `/user/profile` | `GET` | JWT | Retrieve user profile |
| `/user/profile` | `POST` | JWT | Update display name and email |

### Workflow Trigger

| Endpoint | Method | Auth | Description |
| :--- | :---: | :---: | :--- |
| `/trigger-workflow` | `POST` | — | Triggers a specific n8n workflow by ID |

---

## 🌐 Deployment

Both services are deployed on **Render**.

### Backend (FastAPI)

1. Connect your GitHub repository to the Render Dashboard.
2. Create a new **Web Service** and configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
3. Add all environment variables from your `.env` file to the Render service settings.

### Frontend (Angular SSR)

1. Create a second **Web Service** for the frontend:
   - **Build Command:** `npm install && npm run build`
   - **Start Command:** `npm run serve:ssr:frontend-dashboard`

### n8n (Workflow Middleware)

1. Deploy n8n as a third **Web Service** on Render (or use n8n Cloud).
2. Configure basic auth using the credentials in `n8n-workflows/.env`.
3. Ensure all 8 workflows are active and the webhook URLs match the backend `.env`.

---

## 🎯 Innovation & Impact

| Dimension | How This Project Excels |
| :--- | :--- |
| **Autonomous Reasoning** | Goes beyond CRUD — the AI reasons about task dependencies, employee skills, budget constraints, and calendar availability before acting |
| **Self-Healing** | No other PM tool automatically reschedules overdue tasks AND cascades the changes to all dependent tasks |
| **Cost Intelligence** | Real-time burn rate analysis derived from actual Trello board state, not manual input |
| **Tool Orchestration** | 7 specialized tools bound to LangChain, invoked dynamically based on user intent with multi-turn execution loops |
| **Production Architecture** | JWT auth, CORS hardening, retry logic, anti-flood protection, session-based memory — not a prototype |

**Key Outcomes:**
- Reduces cognitive overload on project managers
- Minimizes delays through proactive, automated rescheduling
- Improves team productivity with skill-based task matching
- Enables data-driven, cost-aware project decisions
- Scales across teams and project types without additional configuration

---

## 🗺 Roadmap

```mermaid
graph LR
    classDef phase fill:#4B8BBE,stroke:#fff,stroke-width:2px,color:#fff;
    classDef feature fill:#cce5ff,stroke:#007bff,stroke-width:1px,color:#333;
    classDef done fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#333;

    P1["Intelligence\nUpgrades"]:::phase
    P2["Automation\nUpgrades"]:::phase
    P3["Management\nUpgrades"]:::phase
    P4["Enterprise\nFeatures"]:::phase

    P1 --> F1["Multi-Agent Router\n(Intent Classifier)"]:::feature
    P1 --> F2["Fuzzy Skill Matching\n(thefuzz library)"]:::feature
    P1 --> F3["Predictive Duration\n(ML Regression)"]:::feature

    P2 --> F4["GitHub Sync\n(DONE)"]:::done
    P2 --> F5["Gmail Alerts\n(DONE)"]:::done
    P2 --> F6["Meeting Transcript\nAI Pipeline"]:::feature

    P3 --> F7["Daily Standup\n(DONE)"]:::done
    P3 --> F8["Sprint Velocity\nTracking"]:::feature

    P4 --> F9["Role-Based Access\nControl (RBAC)"]:::feature
    P4 --> F10["Audit Logging\nDashboard"]:::feature
```

### Intelligence Upgrades

| Feature | Description | Technology |
| :--- | :--- | :--- |
| **Multi-Agent Router** | Gatekeeper agent routes requests to specialized agents (Planner, Executor, Status) to reduce latency | LangChain `RouterChain` |
| **Fuzzy Skill Matching** | Upgrade auto-assignment to use fuzzy string matching against the employee skills roster | `thefuzz` library |
| **Predictive Duration** | Replace heuristic duration rules with a regression model trained on historical Trello card completion data | Scikit-Learn |

### Automation Upgrades

| Feature | Status | Description | Technology |
| :--- | :---: | :--- | :--- |
| **GitHub Sync** | ✅ Done | Listens for GitHub push events; `Started #42` moves card to Doing, `Fixed #42` moves card to Done | n8n + GitHub Webhooks |
| **Gmail Emergency Alerts** | ✅ Done | Dispatches urgent Gmail to assignees when tasks are flagged as critical/urgent | Gmail OAuth via n8n |
| **Meeting Transcript AI Pipeline** | 🔜 Planned | FlowSync workflow: Zoom transcript → Gemini AI summary → Google Sheets + Trello tasks + Slack notification (workflow exists but is currently inactive) | n8n + Gemini API + Google Sheets |

### Management Upgrades

| Feature | Status | Description | Technology |
| :--- | :---: | :--- | :--- |
| **Daily Standup Report** | ✅ Done | Automated cron job at 9 AM reads all Trello columns, formats a structured standup, and posts to Slack | n8n Cron + Slack API |
| **Sprint Velocity Tracking** | 🔜 Planned | Calculate and visualize team velocity based on completed story points per sprint | Chart.js + MongoDB |

### Enterprise Features

| Feature | Description | Technology |
| :--- | :--- | :--- |
| **Role-Based Access Control** | Add `role` field (Admin/Manager/Dev) to User model with FastAPI middleware permission checks | FastAPI `Depends` |
| **Audit Logging** | Record all API actions to a `logs` collection with user identity, action type, and timestamp; expose via dashboard | MongoDB + Angular |

---

## 📄 License

Distributed under the [MIT License](LICENSE).

---

<p align="center">
  Architected and built by <br><br>
  <a href="https://github.com/ruthwikreddy07"><strong>Ruthwik Reddy</strong></a> 
  &nbsp;•&nbsp;
  <a href="https://github.com/Ninishareddy49"><strong>Ninisha Reddy</strong></a>
  &nbsp;•&nbsp;
  <a href="https://github.com/ashureddy02"><strong>Ashritha Reddy</strong></a>
</p>
