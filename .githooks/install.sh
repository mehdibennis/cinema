#!/bin/bash
# Install Git hooks for Cinema API project

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Setting up Git hooks..."

# Configure Git to use .githooks directory
git config core.hooksPath .githooks

# Make hooks executable
chmod +x "$SCRIPT_DIR/pre-commit"

echo "Git hooks configured to use .githooks directory"
echo "Pre-commit hook is now active"
