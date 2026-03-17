<p align="center">
  <img src="https://img.shields.io/badge/Angular-19-DD0031?style=for-the-badge&logo=angular&logoColor=white" alt="Angular 19" />
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB" />
  <img src="https://img.shields.io/badge/AI-Groq%20%7C%20Gemini-blueviolet?style=for-the-badge&logo=google&logoColor=white" alt="AI" />
  <img src="https://img.shields.io/badge/n8n-Workflows-EA4B71?style=for-the-badge&logo=n8n&logoColor=white" alt="n8n" />
</p>

<h1 align="center">🤖 Autonomous AI Project Manager</h1>

<p align="center">
  <strong>An intelligent, tool-driven AI agent architecture that autonomously reasons, plans, and executes project management workflows — powered by Groq (Llama 3.1), Gemini Embeddings, and Pinecone Vector Memory.</strong>
</p>

## 🚀 Why This Project Stands Out

- Combines AI + real-world tools (Trello, Slack, Calendar)
- Implements autonomous agent architecture
- Includes self-healing scheduling system
- Production-ready full-stack system

---

# 🚀 AI Project Manager Agent – Summary

## 🔎 Problem It Solves

Traditional project management suffers from:
- Fragmented tools (Trello, Slack, Calendar used separately)
- Manual planning & monitoring
- Poor task allocation based on skills
- Budget overruns & missed deadlines
- No proactive risk detection

Managers constantly track dependencies, deadlines, and costs manually — leading to inefficiencies.

## 💡 Proposed Solution

An Autonomous AI Project Management Agent powered by:
- Large Language Models (LLMs)
- Agentic workflows
- RAG (Retrieval Augmented Generation)
- Real-time tool integrations
- Human-in-the-loop approval

It converts high-level goals → structured execution plans → monitored execution → self-healing adjustments.

## 🧠 How It Works (End-to-End Flow)

1. **User enters a high-level goal**
   → *"Build a mobile app"*
2. **AI breaks it into structured tasks**
   → Development, Testing, Deployment, etc.
3. **Tasks are:**
   - Auto-assigned based on skills
   - Given smart timelines
   - Budget-estimated
4. **Manager reviews & approves plan**
5. **AI executes:**
   - Creates Trello tasks
   - Schedules meetings
   - Sends Slack updates
   - Tracks progress
   - Adjusts delays automatically

## 🛠 Core Technologies

### Backend
- Python + FastAPI
- JWT Authentication
- MongoDB (users, employees, chat history)

### AI Brain
- Groq (Llama 3.1 / 3.3 models)
- LangChain (tool orchestration)
- Gemini embeddings
- Pinecone (vector memory)

### Integrations
- Trello (task management)
- Slack (alerts & updates)
- Google Calendar (meeting scheduling)
- n8n (workflow automation)

### Frontend
- Angular dashboard
- Chat-based interaction
- One-click approval system

## ⭐ Key Capabilities

### 1️⃣ Intelligent Planning
- Task breakdown from goals
- Dependency mapping
- Topological sorting
- Smart timeline skipping weekends
- Budget forecasting

### 2️⃣ Skill-Based Assignment
Matches tasks to employees using:
- Roles
- Skills
- Hourly rates

### 3️⃣ Self-Healing System
- Detects overdue tasks
- Automatically reschedules
- Adjusts dependent tasks
- Sends alerts

### 4️⃣ RAG Memory
- Upload documents
- Stores embeddings in Pinecone
- Retrieves project knowledge when asked

### 5️⃣ Human-in-the-Loop Safety
- Managers approve plans
- AI avoids high-risk actions without validation
- Transparent explainable decisions

## 🔥 Advanced Capabilities

- 🔐 JWT-based authentication & secure APIs  
- 💬 Session-based chat memory with MongoDB  
- ⚡ Automatic focus-time scheduling in Google Calendar  
- 🚨 Smart alert system for urgent tasks (email + Slack)  
- 🔁 Fault-tolerant execution with retry mechanisms  
- 🧠 Dynamic system prompt with real-time team context  
- 🧩 Intelligent multi-tool decision engine  
- 📊 Financial burn analysis & cost tracking  
- 📂 Autonomous document ingestion & vector storage 

## 🎯 Innovation

- Autonomous reasoning beyond traditional PM tools
- Agentic AI that plans + executes + monitors
- Self-healing project workflows
- Cost-aware AI decision-making
- Real-time risk intelligence

## 🌍 Impact

- Reduces cognitive overload
- Improves productivity
- Minimizes human error
- Enables faster decisions
- Scalable across teams
- Practical for real-world deployment

## 🏁 Final Conclusion

This project demonstrates how an Autonomous AI Agent can transform project management from a manual coordination process into an intelligent, proactive, self-managing system — while keeping humans in control for critical decisions.

It combines:
- AI reasoning
- Workflow automation
- Real-time integrations
- Risk control mechanisms

to build a next-generation intelligent project management platform.

---

# Project Overview: AI Project Manager Agent

This project is an autonomous AI Project Manager designed to assist teams by managing tasks, scheduling meetings, planning projects, tracking budgets, and maintaining project documentation. It acts as a central brain that connects various tools (Trello, Google Calendar, Slack, MongoDB) using a Large Language Model (LLM) to reason and execute complex workflows.

---

## 1. Technology Stack

Here is the breakdown of the technologies used, where they are used, and for what purpose:

### Core Backend & Language
- **Python**: The primary programming language for all logic.
- **FastAPI (`server.py`)**: The web framework used to build the REST API. It handles HTTP requests for chat, file uploads, and user management.
- **Uvicorn/Starlette**: Implicitly used by FastAPI for serving the application.

### Artificial Intelligence (The Brain)
- **Groq API (`server.py`, `agent.py`)**: Used to access high-speed LLMs (specifically Llama-3.1-8b-instant and Llama-3.3-70b-versatile). This is the "brain" that processes user input and decides which tools to call.
- **LangChain (`server.py`, `agent.py`)**: The orchestration framework used to bind the LLM with tools (functions) and manage chat history/context.
- **Google Generative AI (Gemini) (`server.py`)**: Used for generating text embeddings (`models/text-embedding-004`) to convert documents into vectors for the memory system.
- **SentenceTransformers (`ingest.py`)**: Used in the standalone ingestion script for local embedding generation (`all-MiniLM-L6-v2`).

### Databases & Memory
- **MongoDB (`server.py`, `create_admin.py`)**: The primary operational database.
  - Stores Users (credentials).
  - Stores Employees (skills, roles, rates).
  - Stores Chat History.
- **Pinecone (`server.py`, `ingest.py`)**: A Vector Database used for Long-Term Memory (RAG). It stores embeddings of uploaded documents so the AI can "recall" project details later.

### Integrations & APIs
- **n8n (`server.py`, `agent.py`)**: A workflow automation tool used as middleware. The AI sends webhooks to n8n to trigger actions in Trello and Slack.
- **Google Calendar API (`calendar_tool.py`)**: Directly accessed via Google Client Library to check availability, find free slots, and book meetings (with Google Meet links).
- **Trello API (`server.py`)**: Accessed both via n8n (for creating cards) and directly via requests (for "healing" the schedule/updating due dates).
- **Slack (`server.py`)**: Accessed via n8n webhooks to send team announcements and meeting notifications.

### Security
- **JWT (JSON Web Tokens)**: Used for securing API endpoints (`OAuth2PasswordBearer`).
- **Passlib (Bcrypt)**: Used for hashing and verifying user passwords.

---

## 2. Key Features & Capabilities

### A. Intelligent Project Planning (`execute_project_plan`)
- **Complex Breakdown**: The AI can take a high-level goal (e.g., "Build a mobile app") and break it down into a JSON list of specific tasks.
- **Dependency Resolution**: It uses a Topological Sorter to order tasks based on dependencies (Task B cannot start until Task A is done).
- **Smart Timeline**: It calculates start and due dates, automatically skipping weekends and company holidays.
- **Budget Estimation**: It calculates project cost based on employee hourly rates (stored in DB) and estimated duration, warning the user if it exceeds the budget.

### B. Task Management & Auto-Assignment
- **Trello Integration**: Creates cards in Trello with labels (Bug, Feature, Urgent).
- **Skill-Based Assignment**: The `auto_assign_owner` function scans the MongoDB employee roster. It matches task descriptions to employee skills or roles (e.g., assigning a "React" task to a "Frontend Developer").

### C. Calendar & Meeting Management (`calendar_tool.py`)
- **Availability Checks**: Can check if a specific time slot is free.
- **Auto-Rescheduling**: If a slot is busy, it searches up to 10 hours ahead to find the next available slot.
- **Booking**: Creates Google Calendar events with Google Meet video conferencing links.
- **Focus Time**: When a task is created, the system attempts to book a "Focus Time" block in the assignee's calendar.

### D. Project Health & Self-Healing
- **Status Checks**: `check_project_status` fetches all Trello cards to identify overdue tasks or tasks due today.
- **Self-Healing Schedule**: `heal_project_schedule` automatically:
  - Moves overdue tasks to the next valid business day.
  - Pushes back dependent tasks if their "blocker" task is delayed.

### E. RAG (Retrieval Augmented Generation)
- **Document Upload**: Users can upload text files via `/upload`.
- **Contextual Recall**: The AI searches Pinecone for relevant document chunks when a user asks questions about the project context (e.g., "What are the requirements in the uploaded PDF?").

---

## 📁 Project Structure

```text
ai-agent-manager/
├── ai-brain/                   # AI Backend System (Python/FastAPI)
│   ├── agent.py                # LangChain & Groq logic for AI reasoning 
│   ├── calendar_tool.py        # Google Calendar integration
│   ├── ingest.py               # RAG document ingestion & Gemini embeddings
│   ├── server.py               # FastAPI server and core endpoints
│   ├── create_admin.py         # Utility script for seeding MongoDB users
│   ├── requirements.txt        # Python dependencies
│   └── .env                    # Backend environment variables
├── frontend-dashboard/         # User Interface (Angular 19)
│   ├── src/                    # UI Source code (Components, Services, Views)
│   ├── angular.json            # Angular project configuration
│   ├── package.json            # Node.js dependencies
│   └── vercel.json             # Vercel deployment config
└── n8n-workflows/              # Automation Workflows
    └── .env                    # Webhook URLs and automation keys
```

---

## 🚀 Getting Started

### Prerequisites
- **Python** 3.10+
- **Node.js** 18+ & npm
- **MongoDB** instance (Atlas or local)
- **Pinecone** account & API key
- **Groq** API key
- **Google Cloud** project with Calendar API enabled

### 1. Clone the Repository
```bash
git clone https://github.com/ruthwikreddy07/AI-Agent-for-Autonomous-Project-Management.git
cd AI-Agent-for-Autonomous-Project-Management
```

### 2. Backend Setup
```bash
cd ai-brain

# Create and activate virtual environment
python -m venv venv
# Windows: venv\Scripts\activate  |  macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in `ai-brain/`:
```env
MONGO_URI=your_mongodb_connection_string
GROQ_API_KEY=your_groq_api_key
HF_TOKEN=your_huggingface_token
PINECONE_API_KEY=your_pinecone_api_key
GOOGLE_API_KEY=your_google_gemini_api_key
JWT_SECRET=your_jwt_secret
N8N_TRELLO_URL=... (and other n8n webhook URLs)
```

```bash
# Ingest project knowledge into Pinecone
python ingest.py

# Start the backend server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend-dashboard
npm install

# Start the development server
ng serve
```
The frontend will be available at `http://localhost:4200`.

### 4. n8n Workflows
Set up an n8n instance and configure the webhook URLs in the `.env` file to enable the 8 automated workflow triggers (Slack bridging, urgent email dispatch, baseline fetching).

---

## 📡 Core API Definitions

| Endpoint | Method | Security | Description |
| :--- | :---: | :---: | :--- |
| `/chat` | `POST` | `JWT` | Main conversational loop; handles intent resolution & tool execution |
| `/upload` | `POST` | `JWT` | Triggers ingestion pipeline, autonomous vectorization, and staging |
| `/approve` | `POST` | `JWT` | Finalizes staged plans, executes Trello/Calendar actions, dispatches alerts |
| `/dashboard/data`| `GET` | `JWT` | Aggregates MongoDB and Trello baselines for burn analysis & charts |
| `/risks` | `GET` | `JWT` | Forces manual refresh loop of active schedule to evaluate timeline integrity |
| `/user/profile` | `POST` | `JWT` | Handles user identity and profile hydration |

---

## 🌐 Deployment (Render)

Both components are configured for deployment on **Render**.

1. Connect your GitHub repository to your Render Dashboard.
2. Initialize a **Web Service** for the FastAPI backend.
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
3. Initialize a **Web Service** for the Angular SSR Frontend.
   - Build Command: `npm install && npm run build`
   - Start Command: `npm run serve:ssr:frontend-dashboard`

---

## 📄 License & Authorship

Distributed under the [MIT License](LICENSE).

<p align="center">
  Architected and built by <a href="https://github.com/ruthwikreddy07">ruthwikreddy07</a>
</p>
