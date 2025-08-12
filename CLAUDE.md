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