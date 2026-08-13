# RAG Engine CI/CD Quick Reference

## Quick Commands

### GitHub Setup
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/rag-engine.git
cd rag-engine

# Configure git
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Create and switch to main branch
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/rag-engine.git

# Push code
git push -u origin main
```

### Docker Commands
```bash
# Build image
docker build -t rag-engine:latest .

# Run container
docker run -it rag-engine:latest

# Run with GPU support
docker run -it --gpus all rag-engine:latest

# Push to registry
docker tag rag-engine:latest ghcr.io/YOUR_USERNAME/rag-engine:latest
docker push ghcr.io/YOUR_USERNAME/rag-engine:latest
```

### Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f rag-engine

# Stop services
docker-compose down

# Remove volumes
docker-compose down -v
```

### Testing & Quality
```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=rag_engine --cov-report=html

# Format code
black rag_engine tests

# Check linting
flake8 rag_engine tests

# Sort imports
isort rag_engine tests
```

### GitHub CLI
```bash
# Install GitHub CLI
winget install GitHub.cli  # Windows
brew install gh           # macOS
sudo apt install gh       # Linux

# Login
gh auth login

# Create pull request
gh pr create --title "Feature: ..." --body "Description"

# View pull requests
gh pr list

# View workflow runs
gh run list

# Watch workflow
gh run watch RUN_ID
```

## Environment Variables

Create `.env` file:
```
HF_TOKEN=your_token
ENVIRONMENT=development
DEVICE=cuda
```

## GitHub Actions Secrets

Set in repo Settings → Secrets:
- `HF_TOKEN` - Hugging Face API token
- `GITHUB_TOKEN` - Auto-generated
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password

## Deployment Commands

### Google Cloud Run
```bash
gcloud run deploy rag-engine \
  --image gcr.io/PROJECT_ID/rag-engine:latest \
  --region us-central1 \
  --set-env-vars HF_TOKEN=$HF_TOKEN
```

### AWS ECS
```bash
aws ecs create-service \
  --cluster rag-cluster \
  --service-name rag-engine \
  --task-definition rag-engine:1
```

### Docker Hub
```bash
docker tag rag-engine:latest USERNAME/rag-engine:latest
docker push USERNAME/rag-engine:latest
```

## File Structure
```
rag_engine/
├── .github/
│   ├── workflows/
│   │   ├── ci-cd.yml          # Main CI/CD pipeline
│   │   └── deploy.yml         # Deployment workflow
│   ├── CONTRIBUTING.md         # Contribution guidelines
│   └── pull_request_template.md
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Pytest fixtures
│   ├── test_embeddings.py
│   ├── test_chunking.py
│   └── test_rag_integration.py
├── .env.example               # Environment template
├── .gitignore                 # Git ignore patterns
├── .dockerignore              # Docker ignore patterns
├── Dockerfile                 # Docker build file
├── docker-compose.yml         # Docker Compose config
├── requirements.txt           # Python dependencies
├── pytest.ini                 # Pytest configuration
└── GITHUB_SETUP.md           # Setup guide
```

## Troubleshooting

### GitHub Actions Failing
1. Check workflow logs in Actions tab
2. Verify secrets are set correctly
3. Run tests locally: `pytest tests/ -v`
4. Check Docker build: `docker build .`

### Docker Issues
```bash
# Clear cache
docker system prune -a

# Rebuild without cache
docker build --no-cache -t rag-engine:latest .

# Check logs
docker logs CONTAINER_ID
```

### Git/GitHub Issues
```bash
# Reset remote
git remote remove origin
git remote add origin https://github.com/USERNAME/rag-engine.git

# Force push (⚠️ use with caution)
git push -f origin main

# View git config
git config --list
```

## Learning Resources
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Docs](https://docs.docker.com)
- [GitHub CLI Docs](https://cli.github.com/manual)
- [Best Practices Guide](./GITHUB_SETUP.md)
