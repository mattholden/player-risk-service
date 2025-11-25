# Player Risk Service

AI-powered player injury and playing time risk assessment service.

## 🎯 Overview

This is an **API-first service** that:
- Fetches sports news articles from NewsAPI
- Uses LLM to analyze injury/playing time risks
- Provides REST API endpoints for integration
- Includes a Streamlit dashboard for internal demos

## 🏗️ Architecture

```
player-risk-service/
├── src/                      # Core API Backend (Python/FastAPI)
│   ├── api/                  # REST API endpoints
│   ├── clients/              # External API clients (NewsAPI, LLM)
│   ├── services/             # Business logic
│   └── main.py               # API entry point
│
├── streamlit_app/            # Internal Dashboard (Streamlit)
│   └── app.py                # Simple UI for demos/business users
│
├── database/                 # Database Layer (SQLAlchemy)
│   ├── models/               # ORM models
│   └── database.py           # Connection management
│
├── scripts/                  # Utility scripts
│   └── init_db.py            # Database initialization
│
└── docker-compose.yml        # All services orchestration
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys:
# - POSTGRES_PASSWORD
# - NEWSAPI_KEY
# - OPENAI_API_KEY (future)
```

### 2. Start Services

```bash
# Start all services (database + backend + streamlit)
docker-compose up --build -d

# View logs
docker-compose logs -f
```

### 3. Access Services

- **Streamlit Dashboard**: http://localhost:8501
- **API Backend**: http://localhost:8000
- **Database**: localhost:5434 (via pgAdmin)

## 🔧 Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start database only
docker-compose up postgres -d

# Run init script
python scripts/init_db.py

# Run backend
python src/main.py

# Run Streamlit (separate terminal)
streamlit run streamlit_app/app.py
```

### Project Structure Explained

**`src/`** - Core backend service
- **API-first design**: Provides REST endpoints for other services
- Contains all business logic, external integrations
- Will use FastAPI for REST API

**`streamlit_app/`** - Internal UI tool
- **Simple dashboard** for business demos
- Calls backend API for all data
- Keep UI minimal - API is the main product

**`database/`** - Data layer
- SQLAlchemy ORM models
- Database connection management
- Shared by backend (Streamlit doesn't access DB directly)

## 📊 Service Flow

```
Streamlit UI (port 8501)
    ↓ HTTP requests
Backend API (port 8000)
    ↓ SQL queries
PostgreSQL Database (port 5434)
```

## 🎯 Use Cases

### Primary: API Integration
```python
# Other services call our API
import requests

response = requests.get("http://api.company.com/player-risk/api/players/jaden-ivey/risk")
risk_data = response.json()
```

### Secondary: Internal Dashboard
- Business demos and presentations
- Manual player upload
- Risk visualization
- Stakeholder review

## 🔑 Key Features (Roadmap)

- [ ] Database setup ✅
- [ ] NewsAPI integration
- [ ] LLM risk analysis
- [ ] REST API endpoints (FastAPI)
- [ ] Background job scheduling
- [ ] Streamlit dashboard UI
- [ ] Alert notifications

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `postgres` | 5434 | PostgreSQL database |
| `backend` | 8000 | Python API service |
| `streamlit` | 8501 | Internal dashboard |

## 📝 Environment Variables

```bash
# Database
POSTGRES_DB=player_risk_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-password>
DATABASE_URL=postgresql://postgres:<password>@localhost:5434/player_risk_db

# APIs
NEWSAPI_KEY=<your-key>
OPENAI_API_KEY=<your-key>  # Future
```

## 🧪 Testing

```bash
# Test database connection
python scripts/test_db_connection.py

# Test API (future)
pytest tests/

# Test Streamlit locally
streamlit run streamlit_app/app.py
```

## 📦 Deployment

The service is designed to be deployed as:
1. **Backend API** - Main service (containerized)
2. **Streamlit Dashboard** - Internal tool (optional)
3. **PostgreSQL** - Database (managed service recommended)

For production:
- Use managed PostgreSQL (AWS RDS, etc.)
- Deploy backend API to K8s or Cloud Run
- Streamlit can be deployed separately or not at all

---

Built with Python, FastAPI, Streamlit, and PostgreSQL
