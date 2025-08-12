#!/usr/bin/env python3
"""Block git commit if ruff check fails, with enhanced features."""
import json
import subprocess
import sys
import re
import os

def main() -> None:
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        sys.exit(0)

    bash_cmd = data.get("tool_input", {}).get("command", "")
    
    # Enhanced matching for various git commit patterns
    if not re.match(r"git\s+commit", bash_cmd):
        sys.exit(0)

    # Check if backend directory exists
    backend_path = os.path.join(os.getcwd(), "backend")
    if not os.path.exists(backend_path):
        # If no backend directory, allow commit
        sys.exit(0)

    # Run Ruff with auto-fixes
    print("🔍 Running ruff check --fix on backend code...", file=sys.stderr)
    ruff_cmd = ["uv", "run", "ruff", "check", "--fix", "backend"]
    
    try:
        proc = subprocess.run(ruff_cmd, text=True, capture_output=True, cwd=os.getcwd())
        
        if proc.returncode != 0:
            # Block commit and show detailed error
            sys.stderr.write(
                "\n❌ Ruff check failed - commit blocked!\n\n"
                "Please fix the following issues:\n"
                "─" * 50 + "\n"
            )
            if proc.stdout:
                sys.stderr.write(proc.stdout + "\n")
            if proc.stderr:
                sys.stderr.write(proc.stderr + "\n")
            sys.stderr.write(
                "─" * 50 + "\n"
                "💡 Tip: Some issues may have been auto-fixed. "
                "Review changes and try committing again.\n"
            )
            sys.exit(2)  # Block the commit
        else:
            # Success - show confirmation
            print("✅ Ruff check passed! Proceeding with commit...", file=sys.stderr)
            sys.exit(0)
            
    except FileNotFoundError:
        sys.stderr.write(
            "\n⚠️  Warning: 'uv' command not found. "
            "Skipping ruff check.\n"
        )
        sys.exit(0)  # Allow commit if uv is not installed
    except Exception as e:
        sys.stderr.write(f"\n⚠️  Hook error: {e}\nAllowing commit to proceed.\n")
        sys.exit(0)  # Fail open on unexpected errors

if __name__ == "__main__":
    main()