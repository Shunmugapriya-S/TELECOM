# RAG Engine - Architecture & Workflow Diagram

## 🔄 Complete CI/CD Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      YOUR LOCAL DEVELOPMENT                         │
│                                                                      │
│  1. Edit Code → 2. git commit → 3. git push → 4. GitHub            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS CI/CD                             │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Lint Job   │→ │  Test Job    │→ │  Build Job   │              │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤              │
│  │ • Black      │  │ • pytest     │  │ • Docker     │              │
│  │ • Flake8     │  │ • Coverage   │  │   build      │              │
│  │ • isort      │  │ • Multiple   │  │ • Push to    │              │
│  │              │  │   Python ver │  │   registry   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│         │                │                   │                      │
│         └────────────────┴───────────────────┘                      │
│                         │                                            │
│  ┌──────────────────────▼─────────────────────────┐                │
│  │         Security & Compliance                  │                │
│  ├──────────────────────────────────────────────┤│                │
│  │ • Trivy (container scanning)                  ││                │
│  │ • Bandit (Python security)                    ││                │
│  │ • Safety (dependency check)                   ││                │
│  │ • License compliance                          ││                │
│  └──────────────────────────────────────────────┘│                │
│         │                                          │                │
│         └─────────────┬────────────────────────────┘                │
│                       │                                              │
│              ✅ ALL CHECKS PASS ✅                                  │
│                       │                                              │
└───────────────────────┼──────────────────────────────────────────────┘
                        ▼
        ┌───────────────────────────────────┐
        │   GitHub Container Registry       │
        │   (ghcr.io/username/rag-engine)  │
        └───────────────────────────────────┘
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
     ┌─────────────┐  ┌─────────┐  ┌────────────┐
     │  GCP Cloud  │  │ AWS ECS │  │ Azure ACI  │
     │    Run      │  │         │  │            │
     └─────────────┘  └─────────┘  └────────────┘
```

---

## 🐳 Local Development Stack

```
┌────────────────────────────────────────────────────────────┐
│                  docker-compose Stack                       │
│                                                             │
│  Port  │ Service         │ Image                            │
│  ────  │ ────────────    │ ──────────────────              │
│  8000  │ RAG Engine      │ rag-engine:latest              │
│  8001  │ Chroma Vector   │ ghcr.io/chroma-core            │
│  6379  │ Redis Cache     │ redis:7-alpine                 │
│  5432  │ PostgreSQL      │ postgres:15-alpine             │
│  9090  │ Prometheus      │ prom/prometheus:latest         │
│         │                 │                                 │
└────────────────────────────────────────────────────────────┘

Start with: docker-compose up -d
```

---

## 📦 Container Architecture

```
┌──────────────────────────────────────────────────┐
│            Docker Image (Multi-Stage)             │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  Stage 1: Builder                           │ │
│  │  • Install build tools                      │ │
│  │  • pip install -r requirements.txt          │ │
│  │  • ~2GB intermediate layer                  │ │
│  └─────────────────────────────────────────────┘ │
│                      │                             │
│                      ▼                             │
│  ┌─────────────────────────────────────────────┐ │
│  │  Stage 2: Runtime                           │ │
│  │  • Copy Python dependencies only            │ │
│  │  • Copy application code                    │ │
│  │  • Non-root user (raguser)                 │ │
│  │  • Health checks configured                 │ │
│  │  • ~500MB final image                      │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
└──────────────────────────────────────────────────┘
```

---

## 🔐 Secrets Management Flow

```
┌──────────────────────────────────────┐
│       Your Environment (Local)        │
│       .env (⚠️  NOT committed)       │
│                                      │
│  HF_TOKEN=xxxxx                     │
│  POSTGRES_PASSWORD=xxxxx            │
│  DOCKER_PASSWORD=xxxxx              │
└──────────────────────────────────────┘
            │
            │ (don't commit)
            │
            ▼
┌──────────────────────────────────────┐
│    GitHub Secrets (Encrypted)         │
│    Settings → Secrets → Actions       │
│                                      │
│  • HF_TOKEN                         │
│  • DOCKER_USERNAME                 │
│  • DOCKER_PASSWORD                 │
│  • Cloud credentials                │
└──────────────────────────────────────┘
            │
            │ (injected at runtime)
            │
            ▼
┌──────────────────────────────────────┐
│    CI/CD Environment Variables        │
│    (Only available during workflow)   │
│                                      │
│  ${{ secrets.HF_TOKEN }}            │
│  ${{ secrets.DOCKER_PASSWORD }}     │
└──────────────────────────────────────┘
```

---

## 🚀 Deployment Flow

```
Development Branch (feature/x)
         │
         ▼
   Pull Request
         │
    ┌────┴────┐
    │          │
    ▼          ▼
[Review]  [Run Tests]
    │          │
    └────┬─────┘
         │ (approved)
         ▼
   Merge to main
         │
         ▼
  Trigger Deploy Workflow
         │
    ┌────┴────────┐
    │             │
    ▼             ▼
[Docker Build]  [Tests Pass]
    │             │
    └────┬────────┘
         │
         ▼
[Push to Registry]
    ghcr.io
         │
    ┌────┴────────┐
    │             │
    ▼             ▼
  [Deploy]   [Deploy]
   GCP Cloud  AWS ECS
   Run        or Azure
```

---

## 📊 Test Execution Flow

```
$ pytest tests/ -v

┌─────────────────────────────────────────────┐
│          Test Discovery                     │
│  Find all test_*.py files in tests/        │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│       Conftest Setup                        │
│  • Load fixtures                            │
│  • Register markers                         │
│  • Configure pytest                         │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│     Test Execution (Parallel)               │
│  ┌──────────────┐  ┌──────────────┐        │
│  │ test_embeddi │  │ test_chunkin │ ...   │
│  │ ngs.py       │  │ g.py         │        │
│  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│     Coverage Report                         │
│  ├─ rag_engine/embeddings.py: 85%         │
│  ├─ rag_engine/chunking.py: 92%           │
│  └─ Total coverage: 88%                    │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│     Results                                 │
│  ✅ 12 passed in 2.34s                     │
│  📊 htmlcov/index.html (coverage report)   │
└─────────────────────────────────────────────┘
```

---

## 🔄 Git Workflow

```
Fork (if contributing)
    │
    ▼
git clone (your fork)
    │
    ├─→ git checkout -b feature/your-feature
    │
    ├─→ Make changes
    │   • Edit code
    │   • Add tests
    │   • Update docs
    │
    ├─→ git add .
    ├─→ git commit -m "meaningful message"
    │
    ├─→ Run tests locally
    │   pytest tests/ -v
    │
    ├─→ Code quality checks
    │   black . && flake8 . && isort .
    │
    ├─→ git push origin feature/your-feature
    │
    └─→ Create Pull Request on GitHub
           ↓
        Code Review
           ↓
        Tests Run (CI/CD)
           ↓
        Merge to main
           ↓
        Deployment
```

---

## 📈 Scaling the Architecture

```
                  Single Developer
                  ├─ git + GitHub
                  ├─ Local testing
                  └─ Manual deployment
                         │
                         ▼
         Small Team (2-5 developers)
         ├─ GitHub Org
         ├─ CI/CD Pipeline
         ├─ Docker Compose
         ├─ PR Reviews
         └─ Staging environment
                         │
                         ▼
      Medium Team (5-20 developers)
      ├─ Multiple services
      ├─ Kubernetes orchestration
      ├─ Monitoring & logging
      ├─ Staging + Production
      └─ CD with automated rollbacks
                         │
                         ▼
    Large Scale (20+ developers)
    ├─ Microservices architecture
    ├─ Service mesh (Istio)
    ├─ Multi-region deployment
    ├─ GitOps (ArgoCD)
    ├─ Advanced monitoring
    └─ Canary/Blue-Green deployments
```

---

## 🛠️ Development Environment Setup

```
┌──────────────────────────────────────────────────────┐
│         Your Development Machine                     │
│                                                      │
│  Required Tools:                                    │
│  ✅ Git                                            │
│  ✅ Python 3.10+                                   │
│  ✅ pip (or poetry)                                │
│  ✅ Docker (optional, for local testing)           │
│  ✅ Docker Compose (optional)                      │
│                                                      │
│  Installation:                                     │
│  $ pip install -r requirements.txt                 │
│  $ pip install pytest black flake8 isort          │
│                                                      │
│  Or use Docker:                                    │
│  $ docker-compose up                              │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 📚 Related Documentation

1. **SETUP_SUMMARY.md** - Overview & checklist
2. **GITHUB_SETUP.md** - Detailed setup guide  
3. **DEPLOYMENT.md** - 5-step quick start
4. **QUICK_REFERENCE.md** - Command cheat sheet
5. **.github/CONTRIBUTING.md** - Contribution rules

---

**Ready to deploy?** Start with **DEPLOYMENT.md** for the 5-step quick start! 🚀
