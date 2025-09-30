## Hosted Version

AnotherAI is available hosted at:
- Web App: https://anotherai.dev
- API: https://api.anotherai.dev

## Running AnotherAI Locally

Ensure `.env` file exists with required API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)

```bash
# Start all services in the background
# Images that have changed will be rebuilt
# Rebuilding images is necessary when dependencies change. By default, the docker-compose exposes "dev" target
# That only contain the dependencies and use volumes for the source code
# In rare cases, using the `--no-cache` can help fix build errors
docker-compose up -d --build

# Stop all services. They can be started again with `docker-compose up -d`
docker-compose stop

# Clean up
# Careful, this will delete all data
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

### Backend Tests (pytest)

Run pytest tests locally:
```bash
uv run pytest backend ...
```



### Frontend Tests (Jest)

Run Jest tests locally:
```bash
cd web
npm test              # Run tests once
yarn test:watch    # Run tests in watch mode
yarn test:coverage # Run tests with coverage
yarn test:ci       # Run tests for CI/CD
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
