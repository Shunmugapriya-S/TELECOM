# GitHub Setup & CI/CD Pipeline Guide

Complete guide to set up your RAG pipeline on GitHub with Docker, CI/CD, and cloud deployment.

## 📋 Table of Contents
1. [GitHub Repository Setup](#github-repository-setup)
2. [Local Git Configuration](#local-git-configuration)
3. [Push Code to GitHub](#push-code-to-github)
4. [GitHub Actions CI/CD](#github-actions-cicd)
5. [Docker Setup](#docker-setup)
6. [Deployment Options](#deployment-options)
7. [Monitoring & Secrets](#monitoring--secrets)

---

## 🚀 GitHub Repository Setup

### Step 1: Create GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. **Repository name**: `rag-engine`
3. **Description**: "RAG Pipeline with Gemma LoRA - CI/CD, Docker, and Cloud Deployment"
4. **Visibility**: Public (or Private if preferred)
5. **Initialize with**:
   - ✅ Add a README file
   - ✅ Add .gitignore (select Python)
   - ✅ Choose a license (MIT recommended)

6. Click **Create repository**

### Example Repository URL
```
https://github.com/YOUR_USERNAME/rag-engine.git
```

---

## 📁 Local Git Configuration

### Step 2: Initialize Git Locally

Open PowerShell in your project directory and run:

```powershell
cd C:\shammu\RAG1\rag_engine

# Initialize Git (if not already done)
git init

# Configure Git user
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: RAG engine with Gemma LoRA integration"

# Add remote repository
git remote add origin https://github.com/YOUR_USERNAME/rag-engine.git

# Set default branch to main
git branch -M main
```

---

## 📤 Push Code to GitHub

### Step 3: Push to GitHub

```powershell
# Push to GitHub
git push -u origin main
```

**If prompted for authentication:**
- Use **GitHub Personal Access Token (PAT)**:
  1. Go to GitHub → Settings → Developer settings → Personal access tokens
  2. Click "Generate new token (classic)"
  3. Select scopes: `repo`, `write:packages`, `delete:packages`
  4. Copy the token and paste when prompted

---

## ⚙️ GitHub Actions CI/CD

### Step 4: Enable GitHub Actions

The CI/CD workflow has been created at `.github/workflows/ci-cd.yml`

**Workflow includes:**
- ✅ **Linting**: Black, Flake8, isort
- ✅ **Testing**: Pytest with coverage
- ✅ **Docker Build**: Multi-stage Docker image
- ✅ **Security**: Trivy vulnerability scanning
- ✅ **Notifications**: GitHub Step Summary

### Step 5: Verify Workflows

1. Go to your GitHub repo → **Actions** tab
2. Select **CI/CD Pipeline** workflow
3. Watch it run on your next push

**View Results:**
- ✅ Commit status checks
- ✅ Pull Request status checks
- ✅ Detailed logs in Actions tab

---

## 🐳 Docker Setup

### Step 6: Build Docker Image Locally

```powershell
# Build Docker image
docker build -t rag-engine:latest .

# Run container
docker run -it --gpus all -v "C:\shammu\RAG1\rag_engine:/app" `
  -e HF_TOKEN=$env:HF_TOKEN `
  rag-engine:latest
```

### Step 7: Use Docker Compose (Local Development)

```powershell
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f rag-engine

# Run tests
docker-compose exec rag-engine pytest tests/ -v

# Stop services
docker-compose down
```

**Services included:**
- RAG Engine (main application)
- Chroma Vector Database
- Redis Cache
- PostgreSQL (metadata)
- Prometheus (monitoring)

### Step 8: Push Docker Image to GitHub Container Registry

```powershell
# Login to GitHub Container Registry
echo $env:GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Tag image
docker tag rag-engine:latest ghcr.io/YOUR_USERNAME/rag-engine:latest

# Push to registry
docker push ghcr.io/YOUR_USERNAME/rag-engine:latest

# Pull from registry
docker pull ghcr.io/YOUR_USERNAME/rag-engine:latest
```

---

## ☁️ Deployment Options

### Option A: Deploy to Google Cloud Run

```powershell
# Authenticate with Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Push to Google Container Registry
docker tag rag-engine:latest gcr.io/YOUR_PROJECT_ID/rag-engine:latest
docker push gcr.io/YOUR_PROJECT_ID/rag-engine:latest

# Deploy to Cloud Run
gcloud run deploy rag-engine `
  --image gcr.io/YOUR_PROJECT_ID/rag-engine:latest `
  --platform managed `
  --region us-central1 `
  --memory 4Gi `
  --set-env-vars HF_TOKEN=$env:HF_TOKEN
```

### Option B: Deploy to AWS ECS

```powershell
# Create ECR repository
aws ecr create-repository --repository-name rag-engine

# Get login token and login
aws ecr get-login-password --region us-east-1 | `
  docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag rag-engine:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rag-engine:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rag-engine:latest
```

### Option C: Deploy to Azure Container Instances

```powershell
# Create Azure Container Registry
az acr create --resource-group myResourceGroup --name myregistry --sku Basic

# Login to ACR
az acr login --name myregistry

# Tag and push
docker tag rag-engine:latest myregistry.azurecr.io/rag-engine:latest
docker push myregistry.azurecr.io/rag-engine:latest

# Deploy
az container create --resource-group myResourceGroup --name rag-engine `
  --image myregistry.azurecr.io/rag-engine:latest `
  --environment-variables HF_TOKEN=$env:HF_TOKEN
```

---

## 🔐 Monitoring & Secrets

### Step 9: Configure GitHub Secrets

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Add the following secrets:

```
GITHUB_TOKEN          = (auto-generated)
HF_TOKEN              = <your_huggingface_token>
DOCKER_USERNAME       = <docker_username>
DOCKER_PASSWORD       = <docker_password>
GCP_PROJECT_ID        = <your_gcp_project>
GCP_SA_KEY            = <gcp_service_account_json>
AWS_ACCESS_KEY_ID     = <aws_access_key>
AWS_SECRET_ACCESS_KEY = <aws_secret_key>
```

### Step 10: Enable Branch Protection

1. Go to **Settings** → **Branches** → **Add rule**
2. Branch name pattern: `main`
3. Enable:
   - ✅ Require status checks to pass
   - ✅ Require code reviews before merge
   - ✅ Dismiss stale pull request approvals

### Step 11: Monitor with GitHub Actions Logs

```powershell
# View workflow runs
gh run list --repo YOUR_USERNAME/rag-engine

# View specific run details
gh run view RUN_ID --repo YOUR_USERNAME/rag-engine

# Watch logs in real-time
gh run watch RUN_ID --repo YOUR_USERNAME/rag-engine
```

---

## 📊 GitHub Pages Documentation

### Step 12: Set Up GitHub Pages

1. Create docs folder:
```powershell
mkdir -p .github/docs
```

2. In repo settings → Pages:
   - Source: Deploy from a branch
   - Branch: main
   - Folder: /docs

3. Add documentation with:
   - Architecture diagrams
   - API documentation
   - Deployment guides

---

## 🧪 Testing & Quality

### Run Tests Locally

```powershell
# Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=rag_engine --cov-report=html

# Run specific test file
pytest tests/test_embeddings.py -v

# Run with markers
pytest tests/ -m "not slow" -v
```

### Code Quality Checks

```powershell
# Format code
black rag_engine tests

# Check code style
flake8 rag_engine tests

# Sort imports
isort rag_engine tests

# Type checking
mypy rag_engine
```

---

## 📋 Checklist

- [ ] GitHub repository created
- [ ] Repository cloned locally
- [ ] All code pushed to GitHub
- [ ] .gitignore configured
- [ ] GitHub Actions enabled
- [ ] Workflows running successfully
- [ ] Docker image building
- [ ] Secrets configured
- [ ] Branch protection enabled
- [ ] Tests passing locally
- [ ] Code quality checks passing
- [ ] Container registry set up
- [ ] Cloud deployment tested
- [ ] Documentation updated
- [ ] CI/CD pipeline fully operational

---

## 🔗 Useful Links

- [GitHub Documentation](https://docs.github.com)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Hugging Face Hub](https://huggingface.co)
- [Gemma Model Card](https://huggingface.co/google/gemma-7b)

---

## 🆘 Troubleshooting

### Docker Build Fails
```powershell
# Clear Docker cache
docker system prune -a

# Rebuild
docker build --no-cache -t rag-engine:latest .
```

### GitHub Actions Timeout
- Increase timeout in workflow YAML
- Optimize Docker image size
- Use caching strategies

### Container Registry Authentication
```powershell
# Regenerate token
gh auth refresh -s write:packages,read:packages

# Re-login
docker logout ghcr.io
docker login ghcr.io
```

### Test Failures in CI
- Run tests locally first: `pytest tests/ -v`
- Check Python version compatibility
- Verify all dependencies installed: `pip install -r requirements.txt`

---

**Need help?** Check the `.github/CONTRIBUTING.md` file for contribution guidelines!
