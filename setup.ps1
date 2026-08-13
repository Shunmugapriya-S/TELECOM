# RAG Engine GitHub CI/CD Setup Script for Windows PowerShell

Write-Host "🚀 RAG Engine - GitHub CI/CD Setup Script" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

# Step 1: Check prerequisites
Write-Host "`n📋 Step 1: Checking prerequisites..." -ForegroundColor Blue

$hasGit = $null -ne (Get-Command git -ErrorAction SilentlyContinue)
$hasDocker = $null -ne (Get-Command docker -ErrorAction SilentlyContinue)
$hasPython = $null -ne (Get-Command python -ErrorAction SilentlyContinue)

if (-not $hasGit) {
    Write-Host "❌ Git is not installed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Git installed" -ForegroundColor Green

if (-not $hasDocker) {
    Write-Host "❌ Docker is not installed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker installed" -ForegroundColor Green

if (-not $hasPython) {
    Write-Host "⚠️  Python not found in PATH" -ForegroundColor Yellow
}

# Step 2: Initialize git
Write-Host "`n📁 Step 2: Initializing Git repository..." -ForegroundColor Blue

if (-not (Test-Path .\.git)) {
    git init
    Write-Host "✓ Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "✓ Git repository already exists" -ForegroundColor Green
}

# Step 3: Configure git
Write-Host "`n⚙️  Step 3: Configuring Git..." -ForegroundColor Blue

$gitEmail = git config user.email
$gitName = git config user.name

if (-not $gitEmail) {
    $gitEmail = Read-Host "Enter your Git email"
    git config --global user.email $gitEmail
}

if (-not $gitName) {
    $gitName = Read-Host "Enter your Git name"
    git config --global user.name $gitName
}

Write-Host "✓ Git configured ($gitName / $gitEmail)" -ForegroundColor Green

# Step 4: Create .env file
Write-Host "`n📝 Step 4: Setting up environment configuration..." -ForegroundColor Blue

if (-not (Test-Path .\.env)) {
    Copy-Item .\.env.example .\.env
    Write-Host "⚠️  Created .env file - Please update with your configuration" -ForegroundColor Yellow
    $continue = Read-Host "Press Enter to continue after updating .env..."
} else {
    Write-Host "✓ .env file already exists" -ForegroundColor Green
}

# Step 5: Add remote repository
Write-Host "`n🔗 Step 5: Configuring remote repository..." -ForegroundColor Blue

$remoteUrl = git config --get remote.origin.url
if (-not $remoteUrl) {
    $remoteUrl = Read-Host "Enter your GitHub repository URL (https://github.com/...)"
    git remote add origin $remoteUrl
    Write-Host "✓ Remote repository added: $remoteUrl" -ForegroundColor Green
} else {
    Write-Host "✓ Remote repository already configured: $remoteUrl" -ForegroundColor Green
}

# Step 6: Install dependencies
Write-Host "`n📦 Step 6: Installing Python dependencies..." -ForegroundColor Blue

if ($hasPython) {
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "⚠️  Python not found. Install dependencies manually: pip install -r requirements.txt" -ForegroundColor Yellow
}

# Step 7: Run tests
Write-Host "`n🧪 Step 7: Running tests..." -ForegroundColor Blue

$hasPytest = $null -ne (Get-Command pytest -ErrorAction SilentlyContinue)
if ($hasPytest) {
    pytest tests/ -v --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Some tests failed" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  pytest not found. Install it: pip install pytest" -ForegroundColor Yellow
}

# Step 8: Build Docker image
Write-Host "`n🐳 Step 8: Building Docker image..." -ForegroundColor Blue

docker build -t rag-engine:latest .
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker image built successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  Docker build failed" -ForegroundColor Yellow
}

# Step 9: Create initial commit
Write-Host "`n💾 Step 9: Creating initial commit..." -ForegroundColor Blue

git add .
git commit -m "Initial commit: RAG engine with CI/CD pipeline"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Changes committed" -ForegroundColor Green
} else {
    Write-Host "✓ Nothing new to commit" -ForegroundColor Green
}

# Step 10: Show next steps
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✓ Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

Write-Host "`n📋 Next steps:" -ForegroundColor Blue
Write-Host "1. Push your code to GitHub:"
Write-Host "   git push -u origin main" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Configure GitHub secrets:"
Write-Host "   - Go to Settings → Secrets and variables → Actions" -ForegroundColor Cyan
Write-Host "   - Add HF_TOKEN, DOCKER_PASSWORD, etc."
Write-Host ""
Write-Host "3. Verify CI/CD workflows:"
Write-Host "   - Go to Actions tab in GitHub" -ForegroundColor Cyan
Write-Host "   - Watch your first workflow run"
Write-Host ""
Write-Host "4. Deploy container:"
Write-Host "   docker run -it rag-engine:latest" -ForegroundColor Yellow
Write-Host ""
Write-Host "5. Use docker-compose for full stack:"
Write-Host "   docker-compose up" -ForegroundColor Yellow
Write-Host ""

Write-Host "📚 Documentation:" -ForegroundColor Blue
Write-Host "- Read GITHUB_SETUP.md for detailed instructions"
Write-Host "- Read .github/CONTRIBUTING.md for contribution guidelines"
Write-Host "- Read QUICK_REFERENCE.md for common commands"
Write-Host ""

Write-Host "✅ Ready to push to GitHub!" -ForegroundColor Green
