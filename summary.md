# Aider Project Summary

## Basic Information

### Authors
<!-- To be filled from git history, run: -->
<!-- git shortlog -sn -->
<!-- git log --format='%aN' | sort -u -->

### Commit History
- First commit: [Date needed - run: git log --reverse --format=%ci | head -1]
- Last commit: [Date needed - run: git log -1 --format=%ci]

### Languages
<!-- To be filled from main codebase, run: -->
<!-- git ls-files | xargs -n1 git blame --line-porcelain | grep "^author " | sort | uniq -c | sort -nr -->
Primary language: Python (>90% of codebase)
Secondary: JavaScript/TypeScript (web interface assets), Various (language test fixtures)

## Project/Code Information

### Architecture
```
.
├── aider/              # Core application logic
│   ├── coders/         # Different coding strategies
│   ├── commands/       # CLI command implementations
│   ├── repo/           # Git integration
│   └── utils/         # Shared utilities
├── benchmark/          # Performance testing
├── scripts/            # Maintenance/CI scripts  
├── tests/              # Comprehensive test suite
└── docs/               # Documentation assets
```

### Core Components
- Interactive coding assistant with LLM integration
- Git-aware code editing workflow
- Multi-language support via test fixtures
- Real-time collaboration features
- Advanced diff/patch management

## Deployment & Usage

### Installation
```bash
pip install aider-chat
```

### Basic Usage
```bash
aider [files...]
```

Running in Docker:

```
docker run -it --user $(id -u):$(id -g) --volume $(pwd):/app -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY paulgauthier/aider-full --model openrouter/deepseek/deepseek-chat-v3-0324:free --weak-model openrouter/google/gemini-2.0-flash-exp:free
```

```
docker run -it --user $(id -u):$(id -g) --volume $(pwd):/app -e GEMINI_API_KEY=$GEMINI_API_KEY paulgauthier/aider-full
```

### Deployment Notes
- Primarily a CLI tool rather than service
- No Docker support observed in current codebase
- Web interface assets present but no server implementation
- Extensive test suite (pytest) for validation

<!-- Add project-specific deployment details as needed -->


## Dev Environment

### Local Setup
```bash
# Clone repository
git clone https://github.com/your-org/aider.git
cd aider

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# Install with development dependencies
pip install -e .[dev]

# Configure API key (one of)
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=your-key
export GEMINI_API_KEY=your-key
```

### Basic Usage
```bash
# Start aider with specific files
python -m aider file1.py file2.txt

# With model selection
python -m aider --model openai/gpt-4-turbo

# Start in git commit mode
python -m aider --commit
```

### Testing & Validation
```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/scrape/test_playwright_disable.py

# Check code formatting
black --check .

# Run linter
flake8 aider/ tests/
```

### Contribution Tips
1. Follow existing code style (Black formatting, Flake8 linting)
2. Add tests for new features in tests/ directory
3. Update documentation in summary.md and help texts
4. Use type hints and docstrings for new code
5. Validate changes against multiple LLM providers
