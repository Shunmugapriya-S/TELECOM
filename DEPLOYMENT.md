# Complete Setup Checklist & Deployment Guide

## 🎯 5-Step Quick Start

### ✅ Step 1: GitHub Repository Setup

**Create GitHub Repository:**
1. Go to [github.com/new](https://github.com/new)
2. Repository name: `rag-engine`
3. Description: "RAG Pipeline with Gemma LoRA - CI/CD & Docker"
4. **Copy the HTTPS URL** (you'll need it next)

**Example URL:** `https://github.com/YOUR_USERNAME/rag-engine.git`

---

### ✅ Step 2: Local Git Configuration

**Open PowerShell in your project directory:**

```powershell
cd C:\shammu\RAG1\rag_engine

# Initialize git (if not already done)
git init

# Configure git
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Create .env file
Copy-Item .env.example .env
# Edit .env and add your HF_TOKEN
```

---

### ✅ Step 3: Push Code to GitHub

```powershell
# Stage all files
git add .

# Initial commit
git commit -m "Initial commit: RAG engine with CI/CD pipeline"

# Add remote repository (replace with YOUR repo URL)
git remote add origin https://github.com/YOUR_USERNAME/rag-engine.git

# Set default branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

**If prompted for authentication:**
- Click "Generate new token" in GitHub
- Or use a GitHub Personal Access Token

---

### ✅ Step 4: Configure GitHub Secrets

**In your GitHub repository:**

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these secrets:

| Secret Name | Value |
|---|---|
| `HF_TOKEN` | Your Hugging Face API token |
| `DOCKER_USERNAME` | Your Docker Hub username (optional) |
| `DOCKER_PASSWORD` | Your Docker Hub token (optional) |

**Where to get HF_TOKEN:**
1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Create new token (read access is fine)
3. Copy and paste into GitHub Secrets

---

### ✅ Step 5: Verify CI/CD Pipeline

**After pushing code:**

1. Go to your GitHub repo → **Actions** tab
2. Click **CI/CD Pipeline** workflow
3. Wait for all checks to pass ✅

**Workflow includes:**
- ✅ Code linting (Black, Flake8, isort)
- ✅ Unit tests (Pytest)
- ✅ Docker image build
- ✅ Security scanning (Trivy)

---

## 🐳 Docker Setup (Local & Cloud)

### Local Testing with Docker

```powershell
# Build Docker image
docker build -t rag-engine:latest .

# Run container
docker run -it -e HF_TOKEN=$env:HF_TOKEN rag-engine:latest

# Test with docker-compose
docker-compose up -d
docker-compose logs -f rag-engine
docker-compose down
```

### Push to GitHub Container Registry

```powershell
# Login to GitHub Container Registry
$env:GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Tag image
docker tag rag-engine:latest ghcr.io/YOUR_USERNAME/rag-engine:latest

# Push
docker push ghcr.io/YOUR_USERNAME/rag-engine:latest

# Pull later
docker pull ghcr.io/YOUR_USERNAME/rag-engine:latest
```

---

## ☁️ Cloud Deployment Options

### Option A: Deploy to Google Cloud Run

```powershell
# Setup
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Deploy
gcloud run deploy rag-engine `
  --source . `
  --platform managed `
  --region us-central1 `
  --memory 4Gi `
  --cpu 2 `
  --set-env-vars HF_TOKEN=$env:HF_TOKEN

# Get URL
gcloud run services describe rag-engine --region us-central1
```

### Option B: Deploy to AWS ECS

```powershell
# Create ECR repository
aws ecr create-repository --repository-name rag-engine

# Push image
aws ecr get-login-password --region us-east-1 | `
  docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker tag rag-engine:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rag-engine:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rag-engine:latest
```

### Option C: Deploy to Azure Container Instances

```powershell
# Create registry
az acr create --resource-group myResourceGroup --name myregistry --sku Basic

# Push image
docker tag rag-engine:latest myregistry.azurecr.io/rag-engine:latest
docker push myregistry.azurecr.io/rag-engine:latest

# Deploy
az container create --resource-group myResourceGroup --name rag-engine `
  --image myregistry.azurecr.io/rag-engine:latest
```

---

## 📁 Project File Structure Created

```
rag_engine/
├── .github/
│   ├── workflows/
│   │   ├── ci-cd.yml          ← Main CI/CD pipeline
│   │   ├── deploy.yml         ← Cloud deployment
│   │   └── security.yml       ← Security scanning
│   ├── CONTRIBUTING.md        ← Contribution guidelines
│   ├── pull_request_template.md
│   └── dependabot.yml         ← Dependency updates
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py            ← Pytest fixtures
│   ├── test_embeddings.py     ← Sample tests
│   ├── test_chunking.py
│   └── test_rag_integration.py
│
├── .env.example               ← Environment template
├── .gitignore                 ← Git ignore patterns
├── .dockerignore              ← Docker ignore
├── Dockerfile                 ← Docker build config
├── docker-compose.yml         ← Local dev stack
├── requirements.txt           ← Python dependencies
├── pytest.ini                 ← Test configuration
│
├── setup.sh                   ← Linux/Mac setup script
├── setup.ps1                  ← Windows setup script
├── GITHUB_SETUP.md            ← Detailed setup guide
├── QUICK_REFERENCE.md         ← Command reference
└── DEPLOYMENT.md              ← This file
```

---

## 🧪 Running Tests Locally

```powershell
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=rag_engine --cov-report=html
# Open htmlcov/index.html to view coverage

# Run specific test file
pytest tests/test_embeddings.py -v

# Run tests matching pattern
pytest tests/ -k "test_sample" -v

# Run with markers
pytest tests/ -m "not slow" -v
```

---

## 🔍 Code Quality Checks

```powershell
# Install dev dependencies
pip install black flake8 isort mypy pylint

# Format code with Black
black rag_engine/ tests/

# Check style with Flake8
flake8 rag_engine/ tests/

# Sort imports
isort rag_engine/ tests/

# Type checking
mypy rag_engine/

# Linting
pylint rag_engine/
```

---

## 📊 Monitoring & Observability

### GitHub Actions Logs
```powershell
# Install GitHub CLI
winget install GitHub.cli

# Login
gh auth login

# View workflow runs
gh run list --repo YOUR_USERNAME/rag-engine

# Watch specific run
gh run watch RUN_ID
```

### Docker Container Logs
```powershell
# View logs
docker-compose logs rag-engine

# Follow logs
docker-compose logs -f rag-engine

# View specific number of lines
docker-compose logs --tail=100 rag-engine
```

### Prometheus Metrics (Optional)
```
http://localhost:9090
```

---

## 🔐 Security Best Practices

✅ **Do:**
- Use GitHub Secrets for all sensitive data (HF_TOKEN, API keys)
- Enable branch protection on `main` branch
- Require pull request reviews before merge
- Run security scans in CI/CD
- Keep dependencies updated with Dependabot
- Use non-root user in Docker containers

❌ **Don't:**
- Commit `.env` files with secrets
- Use `latest` tag in production
- Skip security scans
- Run containers with `--privileged`
- Store credentials in code

---

## 🚨 Troubleshooting

### Issue: `git push` fails
**Solution:**
```powershell
# Check remote
git remote -v

# Update remote URL
git remote set-url origin https://github.com/YOUR_USERNAME/rag-engine.git

# Try push again
git push -u origin main
```

### Issue: Docker build fails
**Solution:**
```powershell
# Clear cache
docker system prune -a

# Rebuild without cache
docker build --no-cache -t rag-engine:latest .

# Check logs
docker logs CONTAINER_ID
```

### Issue: Tests fail locally but pass in CI/CD
**Solution:**
```powershell
# Check Python version
python --version

# Install exact versions from requirements.txt
pip install -r requirements.txt --force-reinstall

# Run tests verbose
pytest tests/ -vv -s
```

### Issue: GitHub Actions timeout
**Solution:**
- Increase timeout in workflow YAML
- Optimize Docker image (use multi-stage build)
- Use caching for pip and Docker layers
- Run tests in parallel

### Issue: Secrets not available in CI/CD
**Solution:**
1. Go to repo Settings → Secrets
2. Verify secret name matches workflow (case-sensitive)
3. For private repos, ensure Actions has access
4. Test locally with: `echo $env:HF_TOKEN`

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `GITHUB_SETUP.md` | Comprehensive setup guide |
| `QUICK_REFERENCE.md` | Common commands reference |
| `DEPLOYMENT.md` | This file - deployment guide |
| `.github/CONTRIBUTING.md` | Contribution guidelines |

---

## 🎓 Learning Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com)
- [GitHub CLI Manual](https://cli.github.com/manual)
- [Hugging Face Hub Guide](https://huggingface.co/docs)
- [Gemma Model Card](https://huggingface.co/google/gemma-7b)

---

## ✅ Final Verification Checklist

- [ ] GitHub repository created
- [ ] All code pushed to GitHub
- [ ] GitHub Secrets configured (HF_TOKEN)
- [ ] CI/CD workflow running successfully
- [ ] All tests passing
- [ ] Docker image builds without errors
- [ ] docker-compose stack working locally
- [ ] Code follows PEP 8 standards
- [ ] Documentation updated
- [ ] Branch protection enabled
- [ ] Pull request template configured
- [ ] Contributing guidelines published
- [ ] Cloud deployment tested (optional)
- [ ] Monitoring configured (optional)

---

## 🆘 Need Help?

1. Check `GITHUB_SETUP.md` for detailed steps
2. Review `.github/CONTRIBUTING.md` for guidelines
3. Look at workflow logs in Actions tab
4. Search GitHub Issues for similar problems
5. Check Docker logs: `docker-compose logs`

**Ready to deploy!** 🚀
