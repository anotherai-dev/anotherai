## Running AnotherAI Locally

Ensure `.env` file exists with required API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down
```

Services will be available at:
- API: http://localhost:8000
- Web App: http://localhost:3000

## Code Quality

Before making any git commits, ensure code quality by running the linter:

```bash
uv run ruff check --fix backend
```

## Testing

### Frontend Tests (Jest)

Run Jest tests locally:
```bash
cd web
npm test              # Run tests once
npm run test:watch    # Run tests in watch mode  
npm run test:coverage # Run tests with coverage
npm run test:ci       # Run tests for CI/CD
```


The Jest test suite covers:
- Pure functions and business logic calculations
- Data transformations and utilities
- String matching algorithms
- Chart utilities and query building
- Experiment business logic
- No UI components, networking, or models

## GitHub Operations

Use `gh` CLI commands (e.g., `gh issue view 124`, `gh pr view 45`) instead of web fetching for GitHub operations since the repository is private.

When writing GitHub comments (on issues or PRs), always identify that the comment was written by Claude Code by adding a signature or identifier, such as:
- "-- Claude Code" at the end of the comment
- Or starting with "Claude Code: " 
- Or including "[via Claude Code]" in the comment

## Team GitHub Usernames

- **Pierre**: pierrevalade
- **Anya**: anyacherniss
- **Jacek**: jacekzimonski
- **Guillaume**: guillaq