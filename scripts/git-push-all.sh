#!/bin/bash
# Push all project repos to GitHub (daily backup of code)
#
# How it works:
# 1. Iterates over a list of local git repositories
# 2. For each repo with uncommitted changes, auto-commits them
# 3. Pushes to the remote (origin)
#
# CUSTOMIZATION:
# - Edit the REPOS array below to list your project directories
# - Adjust the commit message format as needed
# - Add to cron: 0 1 * * * /path/to/git-push-all.sh
set -euo pipefail

# CUSTOMIZE: List your project repositories here
REPOS=(
    # /root/brain
    # /root/my-project
    # /root/my-other-project
    # /root/scripts
)

for repo in "${REPOS[@]}"; do
    if [ -d "$repo/.git" ]; then
        cd "$repo"
        # Check for uncommitted changes (staged or unstaged)
        if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
            git add -A
            git commit -m "auto: daily sync $(date +%Y-%m-%d)" 2>/dev/null || true
        fi
        git push origin HEAD 2>/dev/null && echo "[ok] $(basename $repo)" || echo "[FAIL] $(basename $repo)"
    fi
done
