#!/usr/bin/env bash
set -euo pipefail

# Append header
echo "# Spider" >> README.md

# Initialize repo
git init

# Set local user (to avoid commit failure)
git config user.name "siddharth"
git config user.email "siddharth@example.com"

# Stage and commit
git add README.md
git commit -m "first commit"

# Rename branch to main
git branch -M main

# Add remote
# If remote already exists, update it
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin https://github.com/siddharthmukund/Spider.git
else
  git remote add origin https://github.com/siddharthmukund/Spider.git
fi

# Push (may prompt for credentials or fail if not authenticated)
if git push -u origin main; then
  echo "Push succeeded"
else
  echo "Push failed (likely authentication issue). Please run 'git push -u origin main' locally to authenticate and push the branch." >&2
fi

echo "Done"