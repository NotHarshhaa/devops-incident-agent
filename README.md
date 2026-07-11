# 🚨 DevOps Incident Agent

> An open-source AI agent that automatically investigates DevOps incidents by analyzing metrics, logs, Kubernetes events, deployments, and CI/CD pipelines — then identifies root causes and recommends fixes.

---

## 🚀 Overview

When production breaks, engineers manually jump between Kubernetes, Prometheus, Grafana, Loki, GitHub, Jenkins, ArgoCD, and cloud consoles to piece together what happened. It's slow, repetitive, and stressful — usually at 2am.

**DevOps Incident Agent** automates the first pass of that investigation. It collects evidence across your stack, reasons over it, and hands you a report with a probable root cause, a confidence score, and a recommended fix — before you've even opened Grafana.

---



## 🎯 Goal

Reduce Mean Time To Resolution (MTTR) by letting AI do the initial investigation. The engineer stays in control and approves every action — the AI just gets you to "here's probably what broke" faster.

---



## 🧠 How It Works

```
Production Alert
      ↓
   Planner
      ↓
Collect Evidence  →  Metrics · Logs · Deployments · K8s · Infra
      ↓
Reasoning Engine
      ↓
Incident Report
      ↓
Engineer Approval
```

---



## 🔍 Example

**Input:**

```
Production API latency increased to 8 seconds.
```

**Agent automatically:**

- ✅ Pulls Prometheus metrics
- ✅ Reads Loki logs
- ✅ Checks Kubernetes events
- ✅ Detects recent deployments
- ✅ Reviews GitHub commits
- ✅ Checks Jenkins pipeline status
- ✅ Flags failing pods
- ✅ Identifies probable root cause
- ✅ Suggests remediation

**Sample trace:**

```
🚨 Alert Received
   → Metrics: CPU normal, Memory normal, Latency ↑
   → Logs: Database timeout errors
   → Deployment: shipped 8 minutes ago
   → Git diff: DB connection pool size changed
   → Confidence: 94%
   → Recommendation: Rollback
```

---



## Features

- 🤖 AI-driven incident investigation
- 📈 Metrics analysis
- 📜 Log analysis
- ☸️ Kubernetes event analysis
- 🚀 Deployment analysis
- 🔄 CI/CD investigation
- 🧠 Root cause analysis with confidence scoring
- 📄 Auto-generated incident reports
- ⚠️ Risk assessment before any remediation
- 👨‍💻 Human-in-the-loop approval — nothing auto-executes
- 📚 Incident memory *(planned)*

---



## Architecture

```
                        User
                         │
                         ▼
                  Incident Agent
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
    Metrics          Kubernetes          CI/CD
        │                │                │
  Prometheus          Events           GitHub
  Grafana              Pods            Jenkins
  Loki                 Nodes           ArgoCD
        └────────────────┼────────────────┘
                         ▼
                AI Reasoning Engine
                         ▼
                  Incident Report
```

---



## Integrations


| Category   | Tools                                   |
| ---------- | --------------------------------------- |
| Monitoring | Prometheus, Grafana, Loki, Alertmanager |
| Kubernetes | Kubernetes API, Helm                    |
| CI/CD      | GitHub, GitHub Actions, Jenkins, ArgoCD |
| Cloud      | AWS, Azure, GCP                         |


---



## Tech Stack

- **Language:** Python
- **API layer:** FastAPI
- **Agent orchestration:** LangGraph
- **LLM:** Gemini (primary) — pluggable with OpenAI / Anthropic via a common interface
- **K8s access:** Kubernetes Python client
- **Data sources:** Prometheus API, Grafana API, Loki API, GitHub API
- **Storage:** PostgreSQL, Redis
- **Deployment:** Docker

> Built LLM-agnostic on purpose — bring your own key (Gemini, OpenAI, or Anthropic) rather than being locked to one provider.

---



## Getting Started

The agent runs **fully offline in mock mode** out of the box — no API key and
no live infrastructure required. Add credentials later to point it at your real
stack.

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # core + test deps
# optional extras:
pip install -e ".[llm,integrations,orchestration,storage]"
```

### 2. Configure (optional)

```bash
cp .env.example .env
# Set LLM_PROVIDER=gemini and GEMINI_API_KEY=... (from https://aistudio.google.com/app/apikey)
# then set MOCK_MODE=false to use the real LLM. Leave MOCK_MODE=true to stay offline.
```

### 3. Run an investigation

CLI:

```bash
incident-agent "Production API latency increased to 8 seconds" --service api --severity critical
```

API server:

```bash
incident-agent --serve            # or: uvicorn incident_agent.main:app --reload
curl -X POST localhost:8000/investigate \
  -H "Content-Type: application/json" \
  -d '{"title":"Production API latency increased to 8 seconds","service":"api","severity":"critical"}'
```

Interactive docs at `http://localhost:8000/docs`.

### 4. Run with Docker

```bash
docker compose up --build         # app + postgres + redis
```

### 5. Run the tests

```bash
pytest -q
```

### API endpoints

| Method | Path                          | Purpose                                  |
| ------ | ----------------------------- | ---------------------------------------- |
| GET    | `/health`                     | Liveness + active LLM provider           |
| POST   | `/investigate`                | Run an investigation, return a report    |
| GET    | `/reports/{id}`               | Fetch a stored report                    |
| POST   | `/reports/{id}/approval`      | Human-in-the-loop approve/reject         |

> ⚠️ **Security note:** the API ships without authentication for local/demo use.
> Put it behind an authenticating gateway or add auth before exposing it on a network.

### Project layout

```
src/incident_agent/
├── config.py          # env-driven settings (mock-mode fallbacks)
├── models/            # Incident, Evidence, RootCause, Report schemas
├── llm/               # pluggable providers (gemini/openai/anthropic/mock) + factory
├── collectors/        # prometheus, loki, kubernetes, github, jenkins (+ mock data)
├── agent/             # planner, reasoning, LangGraph graph (+ pure-python fallback)
├── api/               # FastAPI routes
├── store.py           # in-memory / redis report store
├── main.py            # FastAPI app
└── cli.py             # command-line entrypoint
```

---



## Roadmap


| Version  | Scope                                                                               |
| -------- | ----------------------------------------------------------------------------------- |
| **v0.1** | Incident planner, Prometheus + Kubernetes + GitHub integration                      |
| **v0.2** | Loki + Jenkins integration, root cause engine                                       |
| **v0.3** | Reflection agent, incident memory, timeline generation                              |
| **v1.0** | Multi-agent investigation, Slack/Teams/Jira integration, dashboard, incident replay |


---



## Why This Project?

Not another AI chatbot wrapper — this solves one specific, real operational problem: getting engineers to a probable root cause faster during an incident, without replacing their judgment.

---



## Contributing

Contributions welcome — DevOps engineers, SREs, platform engineers, and AI engineers alike. Open an issue or PR.

---



## License

Apache License 2.0

---

⭐ Star the repo if you believe AI should help engineers solve incidents — not replace them.