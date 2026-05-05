#!/bin/bash
# Git pre-commit hook for ApexForge AI
# Install: cp pre-commit-hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

echo "🔒 Running security checks before commit..."

# Check if .env exists in staging area
if git diff --cached --name-only | grep -q "\.env$"; then
    echo "❌ ERROR: Attempting to commit .env file with secrets!"
    echo "   Remove it: git reset HEAD .env && rm .env"
    echo "   Add to .gitignore if not already there"
    exit 1
fi

# Check for any .env files
if git ls-files | grep -q "^\.env"; then
    echo "❌ ERROR: .env file is tracked in git!"
    echo "   Remove it: git rm --cached .env"
    exit 1
fi

# Run Python security check
if [ -f "security_check.py" ]; then
    python security_check.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ Security check failed!"
        echo "   Fix the issues above before committing."
        exit 1
    fi
fi

echo "✅ Security checks passed!"
exit 0
