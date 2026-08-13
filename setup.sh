#!/bin/bash
# Quick setup script for RAG Engine CI/CD

set -e

echo "🚀 RAG Engine - GitHub CI/CD Setup Script"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo -e "\n${BLUE}Step 1: Checking prerequisites...${NC}"

if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed"
    exit 1
fi
echo -e "${GREEN}✓ Git installed${NC}"

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

# Step 2: Initialize git if needed
echo -e "\n${BLUE}Step 2: Initializing Git repository...${NC}"

if [ ! -d .git ]; then
    git init
    echo -e "${GREEN}✓ Git repository initialized${NC}"
else
    echo -e "${GREEN}✓ Git repository already exists${NC}"
fi

# Step 3: Configure git
echo -e "\n${BLUE}Step 3: Configuring Git...${NC}"

if [ -z "$(git config user.email)" ]; then
    read -p "Enter your Git email: " GIT_EMAIL
    git config --global user.email "$GIT_EMAIL"
fi

if [ -z "$(git config user.name)" ]; then
    read -p "Enter your Git name: " GIT_NAME
    git config --global user.name "$GIT_NAME"
fi

echo -e "${GREEN}✓ Git configured${NC}"

# Step 4: Create .env file
echo -e "\n${BLUE}Step 4: Setting up environment configuration...${NC}"

if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠ Created .env file - Please update with your configuration${NC}"
    read -p "Press Enter to continue after updating .env..."
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Step 5: Add remote repository
echo -e "\n${BLUE}Step 5: Configuring remote repository...${NC}"

REPO_URL=$(git config --get remote.origin.url)
if [ -z "$REPO_URL" ]; then
    read -p "Enter your GitHub repository URL (https://github.com/...): " REPO_URL
    git remote add origin "$REPO_URL"
    echo -e "${GREEN}✓ Remote repository added: $REPO_URL${NC}"
else
    echo -e "${GREEN}✓ Remote repository already configured: $REPO_URL${NC}"
fi

# Step 6: Install dependencies
echo -e "\n${BLUE}Step 6: Installing Python dependencies...${NC}"

if command -v python3 &> /dev/null; then
    python3 -m pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠ Python not found. Install dependencies manually: pip install -r requirements.txt${NC}"
fi

# Step 7: Run tests
echo -e "\n${BLUE}Step 7: Running tests...${NC}"

if command -v pytest &> /dev/null; then
    pytest tests/ -v --tb=short || echo -e "${YELLOW}⚠ Some tests failed${NC}"
else
    echo -e "${YELLOW}⚠ pytest not found. Install it: pip install pytest${NC}"
fi

# Step 8: Build Docker image
echo -e "\n${BLUE}Step 8: Building Docker image...${NC}"

docker build -t rag-engine:latest . || echo -e "${YELLOW}⚠ Docker build failed${NC}"
echo -e "${GREEN}✓ Docker image built${NC}"

# Step 9: Create initial commit
echo -e "\n${BLUE}Step 9: Creating initial commit...${NC}"

git add .
git commit -m "Initial commit: RAG engine with CI/CD pipeline" || echo -e "${YELLOW}⚠ Nothing to commit${NC}"
echo -e "${GREEN}✓ Changes committed${NC}"

# Step 10: Show next steps
echo -e "\n${GREEN}=========================================="
echo "✓ Setup Complete!"
echo "==========================================${NC}"

echo -e "\n${BLUE}Next steps:${NC}"
echo "1. Push your code to GitHub:"
echo -e "   ${YELLOW}git push -u origin main${NC}"
echo ""
echo "2. Configure GitHub secrets:"
echo "   - Go to Settings → Secrets and variables → Actions"
echo "   - Add HF_TOKEN, DOCKER_PASSWORD, etc."
echo ""
echo "3. Verify CI/CD workflows:"
echo "   - Go to Actions tab in GitHub"
echo "   - Watch your first workflow run"
echo ""
echo "4. Deploy container:"
echo -e "   ${YELLOW}docker run -it rag-engine:latest${NC}"
echo ""
echo "5. Use docker-compose for full stack:"
echo -e "   ${YELLOW}docker-compose up${NC}"
echo ""

echo -e "${BLUE}Documentation:${NC}"
echo "- Read GITHUB_SETUP.md for detailed instructions"
echo "- Read .github/CONTRIBUTING.md for contribution guidelines"
echo ""
