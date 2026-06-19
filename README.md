# DRMS - Digital Records Management System

A web-based system for managing and organizing digital records and documents.

![dashboard.png](img/dashboard.png)

## Features Implemented

### Core Document Management
- 📄 Create, update, archive documents with file uploads
- 📜 Version history with file versioning support
- 💬 Document comments
- 📊 Document activity history tracking

### User & Access Control
- 🔐 User authentication with session management
- 👥 Role-based access control (RBAC) with permissions
- 🔑 Custom user permissions
- 📝 Login history tracking

### Document Organization
- 🏷️ Categories and subcategories
- 🔖 Tags and Stages

### Collaboration
- 🤝 Document sharing with date ranges
- ⏰ Reminders with user assignments
- 📈 Dashboard

### AI / LLM Features
- 🔍 Natural language document search (LangGraph agent extracts structured filters)
- 📝 AI-generated document summaries
- 💬 Document chat / RAG (conversational Q&A using Qdrant + Ollama)

### Telegram Bot
- 🤖 Full Telegram bot interface (`/documents`, `/mydocuments`, `/reminders`, `/search`)
- 🔗 Account linking via `/login` / `/unlink`
- 🔔 Automated reminder notifications pushed to Telegram

### Document Processing
- 📑 Automatic text extraction (PDF, DOCX, XLSX, PPTX, TXT)
- 🧠 Background vector embedding for RAG (Celery + Qdrant)
- ⚙️ Asynchronous task queue (Celery worker + beat scheduler)

![document.png](img/document.png)

## Tech Stack

- **Backend:** Python 3.14+, FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery
- **Frontend:** Next.js 16, React 19, TypeScript, TailwindCSS

## How to Run Locally

```bash
docker compose up
```

- **Backend:** http://localhost:8000
- **Frontend:** http://localhost:3000


## Project Status

🚧 **WIP** - Work in Progress
