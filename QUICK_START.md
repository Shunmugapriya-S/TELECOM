# 🚀 RAG Engine - 5-Minute Quick Start

## ⚡ TLDR - Get Running in 5 Steps

### Step 1️⃣: Create GitHub Repository (1 min)
```
1. Go to https://github.com/new
2. Repository name: rag-engine
3. Click "Create repository"
4. Copy the HTTPS URL (you'll need it next)
```

**Example URL:** `https://github.com/YOUR_USERNAME/rag-engine.git`

---

### Step 2️⃣: Push Your Code to GitHub (2 min)

Open PowerShell in `C:\shammu\RAG1\rag_engine` and run:

```powershell
# One-time setup
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# Add, commit, and push
git init
git add .
git commit -m "Initial commit: RAG engine with CI/CD"
git remote add origin https://github.com/YOUR_USERNAME/rag-engine.git
git branch -M main
git push -u origin main
```

**If you get a password prompt:**
- Use a [GitHub Personal Access Token](https://github.com/settings/tokens)
- Or use GitHub CLI: `gh auth login`

---

### Step 3️⃣: Configure GitHub Secrets (1 min)

1. Go to your GitHub repo
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add `HF_TOKEN`:
   - **Name:** `HF_TOKEN`
   - **Value:** Get from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

5. Click **"Add secret"**

---

### Step 4️⃣: Watch CI/CD Run (1 min)

1. Go to your GitHub repo → **Actions** tab
2. Click **CI/CD Pipeline** workflow
3. Watch it run automatically! 

**What happens:**
- ✅ Code gets linted (formatting checked)
- ✅ Tests run (pytest)
- ✅ Docker image builds
- ✅ Security scan runs
- ✅ If all pass → **SUCCESS!** 🎉

---

### Step 5️⃣: Test Locally (Optional)

```powershell
# Run tests
pytest tests/ -v

# Run with docker-compose (all services)
docker-compose up -d
docker-compose logs -f rag-engine
docker-compose down
```

---

## ✅ You're Done!

Your RAG pipeline now has:
- ✅ Automatic testing on every push
- ✅ Docker containerization
- ✅ GitHub Actions CI/CD
- ✅ Security scanning
- ✅ Professional setup

---

## 📚 Need More Details?

| Document | For What |
|----------|----------|
| **DEPLOYMENT.md** | 5-step setup with explanations |
| **GITHUB_SETUP.md** | Comprehensive detailed guide |
| **QUICK_REFERENCE.md** | Command cheat sheet |
| **ARCHITECTURE.md** | Diagrams & visual workflows |
| **.github/CONTRIBUTING.md** | Contribution guidelines |

---

## 🔐 Important: Protect Your `main` Branch

1. Go to repo **Settings** → **Branches**
2. Click "Add rule"
3. Branch name: `main`
4. Check: ✅ "Require status checks to pass before merging"
5. Check: ✅ "Require code reviews before merge"
6. Click "Create"

Now all PRs must pass tests before merging! 

---

## 🐳 Local Development with Docker

```powershell
# Start all services (RAG Engine, Chroma, Redis, Postgres, Prometheus)
docker-compose up -d

# View logs
docker-compose logs -f rag-engine

# Run tests in container
docker-compose exec rag-engine pytest tests/ -v

# Stop services
docker-compose down
```

**Services available:**
- RAG Engine: http://localhost:8000
- Chroma Vector DB: http://localhost:8001
- Redis: localhost:6379
- PostgreSQL: localhost:5432
- Prometheus: http://localhost:9090

---

## 🚨 Troubleshooting

### Git push fails
```powershell
git remote -v
git remote set-url origin YOUR_GITHUB_URL
git push -u origin main
```

### Tests fail locally
```powershell
pip install -r requirements.txt --force-reinstall
pytest tests/ -vv
```

### Docker build fails
```powershell
docker system prune -a
docker build --no-cache -t rag-engine:latest .
```

### Workflow doesn't run
1. Check you have secrets configured
2. Check your branch is `main`
3. Check `.github/workflows/ci-cd.yml` exists
4. Go to Actions tab and look for errors

---

## 🎓 Learning Path

```
Day 1: Setup
└─ Complete 5 steps above
└─ See CI/CD run successfully

Day 2: Understand
└─ Read GITHUB_SETUP.md
└─ Read ARCHITECTURE.md
└─ Understand the workflows

Day 3: Develop
└─ Make code changes
└─ Create pull request
└─ See tests run automatically

Day 4: Deploy
└─ Deploy to cloud (optional)
└─ Monitor your app
└─ Update documentation
```

---

## 📊 Files Created for You

```
NEW FILES CREATED:
✅ .github/
   ├─ workflows/ci-cd.yml          (Main CI/CD pipeline)
   ├─ workflows/deploy.yml         (Cloud deployment)
   ├─ workflows/security.yml       (Security scanning)
   ├─ CONTRIBUTING.md
   ├─ pull_request_template.md
   └─ dependabot.yml

✅ tests/
   ├─ conftest.py                  (Shared fixtures)
   ├─ test_embeddings.py
   ├─ test_chunking.py
   └─ test_rag_integration.py

✅ Docker & Config
   ├─ Dockerfile                   (Container build)
   ├─ docker-compose.yml          (Local dev stack)
   ├─ .gitignore                  (Git ignore patterns)
   ├─ .dockerignore               (Docker ignore)
   ├─ .env.example                (Environment template)
   ├─ pytest.ini                  (Test config)
   └─ requirements.txt            (Updated dependencies)

✅ Documentation
   ├─ GITHUB_SETUP.md             (Comprehensive guide)
   ├─ DEPLOYMENT.md               (5-step start)
   ├─ SETUP_SUMMARY.md            (Overview)
   ├─ QUICK_REFERENCE.md          (Cheat sheet)
   ├─ ARCHITECTURE.md             (Diagrams)
   └─ QUICK_START.md              (This file)

✅ Setup Scripts
   ├─ setup.ps1                   (Windows)
   └─ setup.sh                    (Linux/Mac)
```

---

## 🎯 What Happens Next

### On Push to GitHub:
```
You push code
    ↓
GitHub detects push
    ↓
Workflow starts automatically
    ↓
┌─ Linting (black, flake8, isort)
├─ Testing (pytest + coverage)
├─ Docker build
└─ Security scan
    ↓
✅ If all pass → Build succeeds!
❌ If any fail → You get notified
```

### On Pull Request:
```
Create PR → Tests run automatically
    ↓
Need review before merging
    ↓
Merge → Triggers deploy workflow (optional)
```

---

## 💡 Pro Tips

1. **Always pull before pushing**
   ```powershell
   git pull origin main
   git push origin main
   ```

2. **Use meaningful commit messages**
   ```powershell
   git commit -m "feat: add embeddings optimization"
   git commit -m "fix: handle null values in chunking"
   git commit -m "docs: update README"
   ```

3. **Run tests locally before pushing**
   ```powershell
   pytest tests/ -v
   black . && flake8 . && isort .
   ```

4. **Check workflow status**
   ```
   GitHub repo → Actions tab → See live status
   ```

5. **Use GitHub CLI for convenience**
   ```powershell
   gh pr create  # Create PR from command line
   gh run watch  # Watch workflow run
   gh run list   # See past runs
   ```

---

## 🆘 Quick Help

**Q: Where's my GitHub repository?**
A: https://github.com/YOUR_USERNAME/rag-engine

**Q: How do I see if tests passed?**
A: GitHub repo → Actions tab → CI/CD Pipeline

**Q: How do I deploy to cloud?**
A: See GITHUB_SETUP.md section "Deployment Options"

**Q: Where are my secrets stored?**
A: Settings → Secrets and variables → Actions

**Q: Can I run this locally?**
A: Yes! `docker-compose up -d`

**Q: Do I need Docker?**
A: No for development, but yes for containerization

---

## 🎉 That's It!

You now have:
- ✅ Professional GitHub repository
- ✅ Automated testing
- ✅ Docker containerization
- ✅ CI/CD pipeline
- ✅ Security scanning
- ✅ Cloud-ready deployment

**Next step:** Complete the 5 steps above! 🚀

---

**Still need help?** Read [GITHUB_SETUP.md](GITHUB_SETUP.md) for detailed instructions.
