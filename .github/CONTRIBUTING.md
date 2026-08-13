# Contributing to RAG Engine

Thank you for your interest in contributing! Please follow these guidelines.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/rag-engine.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Set up development environment:

```bash
pip install -r requirements.txt
pip install black flake8 pytest pytest-cov
```

## Development Workflow

1. Make your changes
2. Run tests: `pytest tests/ -v`
3. Check code quality: `black . && flake8 . && isort .`
4. Commit with descriptive message
5. Push to your fork
6. Open a Pull Request

## Code Standards

- Follow PEP 8
- Use type hints where possible
- Write tests for new features
- Update documentation
- Keep commits atomic

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Squash commits if necessary
4. Write clear PR description
5. Link related issues

## Testing

Run tests locally before submitting:

```bash
pytest tests/ -v --cov=rag_engine
```

## Questions?

Open an issue or start a discussion!
