"""
Security check script for ApexForge AI.
Run this before committing to ensure no secrets are exposed.
"""

import os
import re
import sys
from pathlib import Path

# Patterns that indicate sensitive data
DANGEROUS_PATTERNS = [
    # Database URLs with actual passwords (not placeholder examples)
    (r'postgresql://[a-zA-Z0-9_]+:[a-zA-Z0-9_]+@[a-z0-9.-]+\.[a-z]{2,}', 'PostgreSQL URL with password'),
    (r'mongodb\+srv://[^:]+:[^@]+@', 'MongoDB URL with password'),
    (r'mysql://[^:]+:[^@]+@', 'MySQL URL with password'),
    # AWS keys
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key ID'),
    # Generic secrets (avoid matching regex patterns themselves)
    (r'(?<!\(\?)password\s*=\s*["\'][^"\']{8,}["\']', 'Hardcoded password'),
    (r'(?<!\(\?)secret\s*=\s*["\'][^"\']{8,}["\']', 'Hardcoded secret'),
    (r'api_key\s*=\s*["\'][^"\']{16,}["\']', 'Hardcoded API key'),
    (r'token\s*=\s*["\'][^"\']{16,}["\']', 'Hardcoded token'),
    # Private keys (not in regex definitions)
    (r'(?<!\(\?)BEGIN PRIVATE KEY', 'Private key'),
    (r'(?<!\(\?)BEGIN RSA PRIVATE KEY', 'RSA Private key'),
    # Real connection strings with actual values (not examples)
    (r'DATABASE_URL\s*=\s*postgresql://\w+:\w+@\w+', 'Database URL with credentials'),
]

# Files to check
CHECK_EXTENSIONS = {'.py', '.txt', '.md', '.json', '.yml', '.yaml', '.toml'}
SKIP_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', '.pytest_cache', 'htmlcov'}

# Files to skip (this script itself, and common false positives)
SKIP_FILES = {'security_check.py', '.env.example', 'pre-commit-hook.sh', '.gitignore'}

# Files that MUST exist and be properly configured
REQUIRED_FILES = ['.env.example', '.gitignore']
FORBIDDEN_FILES = ['.env']


def scan_file(filepath: Path) -> list:
    """Scan a single file for dangerous patterns."""
    issues = []

    # Skip certain files that cause false positives
    if filepath.name in SKIP_FILES:
        return issues

    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip comment lines explaining patterns
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('*'):
                continue
            # Skip lines that are clearly regex definitions or code examples
            if stripped.startswith('(r\'') or stripped.startswith('(r"') or 'pattern' in stripped.lower():
                continue

            for pattern, description in DANGEROUS_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip lines with obvious placeholder values
                    lower_line = line.lower()
                    if any(x in lower_line for x in ['your_', 'example', 'placeholder', 'username', 'password']):
                        continue
                    # Skip lines that are clearly example/documentation
                    if '```' in line or '<code>' in line or line.count('`') >= 2:
                        continue

                    issues.append({
                        'file': str(filepath),
                        'line': line_num,
                        'content': line.strip()[:80],
                        'issue': description
                    })
    except Exception as e:
        issues.append({
            'file': str(filepath),
            'line': 0,
            'content': f'Error reading file: {e}',
            'issue': 'File read error'
        })

    return issues


def check_gitignore() -> list:
    """Check that .gitignore properly excludes sensitive files."""
    issues = []
    gitignore_path = Path('.gitignore')

    if not gitignore_path.exists():
        issues.append({
            'file': '.gitignore',
            'line': 0,
            'content': 'File not found',
            'issue': 'CRITICAL: .gitignore is missing!'
        })
        return issues

    content = gitignore_path.read_text(encoding='utf-8')
    required_patterns = ['.env', '*.key', '*.pem', 'secrets']

    for pattern in required_patterns:
        if pattern not in content:
            issues.append({
                'file': '.gitignore',
                'line': 0,
                'content': f'Missing pattern: {pattern}',
                'issue': f'.gitignore should exclude {pattern}'
            })

    return issues


def check_env_example() -> list:
    """Check that .env.example exists and doesn't contain real credentials."""
    issues = []
    example_path = Path('.env.example')

    if not example_path.exists():
        issues.append({
            'file': '.env.example',
            'line': 0,
            'content': 'File not found',
            'issue': '.env.example template is missing'
        })
        return issues

    content = example_path.read_text(encoding='utf-8')

    # Check for placeholders
    if 'your_' not in content.lower() and 'example' not in content.lower():
        issues.append({
            'file': '.env.example',
            'line': 0,
            'content': 'No placeholder values detected',
            'issue': '.env.example should use placeholder values like YOUR_PASSWORD'
        })

    # Check it doesn't contain real-looking credentials
    if re.search(r'[a-zA-Z0-9]{20,}', content):
        suspicious = re.findall(r'[a-zA-Z0-9]{20,}', content)
        for match in suspicious[:3]:  # Check first 3
            if not any(x in match.lower() for x in ['example', 'your', 'placeholder', 'test']):
                issues.append({
                    'file': '.env.example',
                    'line': 0,
                    'content': match[:40],
                    'issue': 'Possible real credential in .env.example?'
                })

    return issues


def main():
    """Run all security checks."""
    all_issues = []

    print("🔒 ApexForge AI Security Check")
    print("=" * 50)

    # Check required/forbidden files
    print("\n📁 Checking required files...")
    for filename in REQUIRED_FILES:
        if Path(filename).exists():
            print(f"  ✅ {filename} exists")
        else:
            print(f"  ❌ {filename} is MISSING")
            all_issues.append({'file': filename, 'issue': 'Required file missing'})

    for filename in FORBIDDEN_FILES:
        if Path(filename).exists():
            print(f"  ⚠️  {filename} exists (should be gitignored)")
        else:
            print(f"  ✅ {filename} not present (good)")

    # Check .gitignore
    print("\n🛡️  Checking .gitignore...")
    all_issues.extend(check_gitignore())
    if not any(i['file'] == '.gitignore' for i in all_issues):
        print("  ✅ .gitignore looks good")

    # Check .env.example
    print("\n📝 Checking .env.example...")
    all_issues.extend(check_env_example())
    if not any(i['file'] == '.env.example' for i in all_issues):
        print("  ✅ .env.example looks good")

    # Scan files for secrets
    print("\n🔍 Scanning files for exposed secrets...")
    scanned = 0
    for root, dirs, files in os.walk('.'):
        # Skip directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if any(file.endswith(ext) for ext in CHECK_EXTENSIONS):
                filepath = Path(root) / file
                scanned += 1
                issues = scan_file(filepath)
                all_issues.extend(issues)

    print(f"  Scanned {scanned} files")

    # Report
    print("\n" + "=" * 50)
    if all_issues:
        print(f"❌ FOUND {len(all_issues)} SECURITY ISSUES:")
        print()
        for issue in all_issues:
            print(f"  🚨 {issue['issue']}")
            print(f"     File: {issue['file']}", end="")
            if issue.get('line'):
                print(f":{issue['line']}")
            else:
                print()
            if issue.get('content'):
                print(f"     Content: {issue['content'][:60]}")
            print()
        print("⚠️  Please fix these issues before committing!")
        return 1
    else:
        print("✅ All security checks passed!")
        print("   Your code is safe to commit.")
        return 0


if __name__ == '__main__':
    sys.exit(main())
