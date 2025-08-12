## Code Quality

Before making any git commits, ensure code quality by running the linter:

```bash
uv run ruff check --fix backend
```

This command will automatically fix any linting issues in the backend code. Always run this before committing to maintain code quality standards.

## Front-End Development

To start the front-end development server:

```bash
cd web
npm run dev
```

This starts the Next.js development server with Turbopack on http://localhost:3000.

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