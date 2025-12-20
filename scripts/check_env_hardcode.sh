#!/bin/bash
# Script to detect hardcoded values that should be environment variables
# Exit code: 0 if no hardcode found, 1 if hardcode detected

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ERRORS=0
WARNINGS=0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 AUDIT ANTI-HARDCODE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Patterns to check (excluding docs, scripts, and test files)
# Note: Fallbacks in config.ts files are acceptable for dev
PATTERNS=(
  "localhost:8000"
  "localhost:3000"
  "localhost:3001"
  "127\.0\.0\.1:8000"
  "127\.0\.0\.1:3000"
  "127\.0\.0\.1:3001"
)

# Secret patterns (should NEVER be hardcoded)
SECRET_PATTERNS=(
  "Bearer [A-Za-z0-9]{20,}"  # JWT tokens
  "AKIA[A-Z0-9]{16}"  # AWS access keys
  "sk_[A-Za-z0-9]{20,}"  # Secret keys
  "secret.*=.*[\"'][^\"']{10,}"  # Secret assignments
)

# Directories to exclude
EXCLUDE_DIRS=(
  "node_modules"
  ".next"
  ".git"
  "archive"
  "__pycache__"
  ".venv"
  "venv"
  "docs"
  "scripts"
  "*.md"
)

# Build exclude pattern for find
EXCLUDE_PATTERN=""
for dir in "${EXCLUDE_DIRS[@]}"; do
  EXCLUDE_PATTERN="${EXCLUDE_PATTERN} -path */${dir} -prune -o"
done

# Helper function to check if a file is in allowed dev-default paths
is_dev_default_file() {
  local file="$1"
  # Allow docker-compose files in any directory
  if [[ "$file" == *"docker-compose"*.yml ]] || [[ "$file" == *"docker-compose"*.yaml ]]; then
    return 0
  fi
  # Allow infra/ directory
  if [[ "$file" == *"infra/"* ]]; then
    return 0
  fi
  # Allow docs/ and scripts/ directories
  if [[ "$file" == *"docs/"* ]] || [[ "$file" == *"scripts/"* ]]; then
    return 0
  fi
  return 1
}

# Helper function to check if a match in backend/app/main.py is in a log message
is_log_message() {
  local file="$1"
  local pattern="$2"
  
  if [[ "$file" != *"backend/app/main.py" ]]; then
    return 1
  fi
  
  # Get the line number(s) where pattern appears
  local line_nums=$(grep -n "$pattern" "$file" 2>/dev/null | cut -d: -f1 || echo "")
  
  if [ -z "$line_nums" ]; then
    return 1
  fi
  
  # Check each line: if it's inside a logger.warning(), logger.info(), print(), or similar
  for line_num in $line_nums; do
    # Get context around the line (3 lines before and after)
    local context=$(sed -n "$((line_num > 3 ? line_num - 3 : 1)),$((line_num + 3))p" "$file" 2>/dev/null)
    
    # Check if context contains log-related keywords
    if echo "$context" | grep -qE "(logger\.(warning|info|error|debug)|logging\.|print\(|log\()"; then
      return 0
    fi
    
    # Also check if the line itself is inside quotes (string literal in log message)
    local line_content=$(sed -n "${line_num}p" "$file" 2>/dev/null)
    if echo "$line_content" | grep -qE "[\"'].*$pattern.*[\"']"; then
      return 0
    fi
  done
  
  return 1
}

# Check each pattern
for pattern in "${PATTERNS[@]}"; do
  echo "Checking for: $pattern"
  
  # Find files (excluding node_modules, .next, .git, docs, scripts, archive)
  FILES=$(find . \
    -type f \
    \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" -o -name "*.yml" -o -name "*.yaml" \) \
    ! -path "*/node_modules/*" \
    ! -path "*/.next/*" \
    ! -path "*/.git/*" \
    ! -path "*/archive/*" \
    ! -path "*/docs/*" \
    ! -path "*/scripts/*" \
    ! -path "*/__pycache__/*" \
    ! -path "*/.venv/*" \
    ! -path "*/venv/*" \
    ! -name "*.md" \
    -exec grep -l "$pattern" {} \; 2>/dev/null || true)
  
  if [ -n "$FILES" ]; then
    HAS_FAIL=false
    HAS_WARN=false
    
    # First pass: collect files
    while IFS= read -r file; do
      if [ -n "$file" ]; then
        # Check if it's an acceptable dev default
        if is_dev_default_file "$file"; then
          HAS_WARN=true
        elif is_log_message "$file" "$pattern"; then
          HAS_WARN=true
        elif [[ "$file" == *"config.ts" ]]; then
          HAS_WARN=true
        else
          HAS_FAIL=true
        fi
      fi
    done <<< "$FILES"
    
    # Second pass: output results
    if [ "$HAS_FAIL" = true ] || [ "$HAS_WARN" = true ]; then
      if [ "$HAS_FAIL" = true ]; then
        echo "  ❌ Found in:"
      else
        echo "  ⚠️  Found in (dev defaults - acceptable):"
      fi
      
      while IFS= read -r file; do
        if [ -n "$file" ]; then
          if is_dev_default_file "$file"; then
            echo "     - $file (⚠️  acceptable: dev default in docker-compose/docs/scripts/infra)"
            WARNINGS=$((WARNINGS + 1))
          elif is_log_message "$file" "$pattern"; then
            echo "     - $file (⚠️  acceptable: log message/example)"
            WARNINGS=$((WARNINGS + 1))
          elif [[ "$file" == *"config.ts" ]]; then
            echo "     - $file (⚠️  acceptable: config fallback)"
            WARNINGS=$((WARNINGS + 1))
          else
            echo "     - $file"
            ERRORS=$((ERRORS + 1))
          fi
        fi
      done <<< "$FILES"
    fi
  else
    echo "  ✅ Not found"
  fi
  echo ""
done

# Special check for frontend-client and frontend-admin (excluding lib/config.ts)
echo "Checking frontend-client and frontend-admin for hardcoded URLs..."
FRONTEND_PATTERNS=(
  "localhost:8000"
  "http://localhost"
  ":8000/"
)

for pattern in "${FRONTEND_PATTERNS[@]}"; do
  FRONTEND_FILES=$(find ./frontend-client ./frontend-admin \
    -type f \
    \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
    ! -path "*/node_modules/*" \
    ! -path "*/.next/*" \
    ! -path "*/lib/config.ts" \
    ! -path "*/docs/*" \
    -exec grep -l "$pattern" {} \; 2>/dev/null || true)
  
  if [ -n "$FRONTEND_FILES" ]; then
    echo "  ⚠️  Found '$pattern' in frontend files (outside lib/config.ts):"
    while IFS= read -r file; do
      if [ -n "$file" ]; then
        # Check if it's a fallback in api.ts (acceptable with warning)
        if [[ "$file" == *"lib/api.ts" ]] && grep -q "process.env.NEXT_PUBLIC_API_BASE_URL.*localhost:8000" "$file" 2>/dev/null; then
          echo "     - $file (⚠️  acceptable: fallback in api.ts, should use lib/config.ts)"
          WARNINGS=$((WARNINGS + 1))
        else
          echo "     - $file"
          ERRORS=$((ERRORS + 1))
        fi
      fi
    done <<< "$FRONTEND_FILES"
  fi
done
echo ""

# Check for hardcoded R2/S3 endpoints (excluding docs and scripts)
echo "Checking for hardcoded R2/S3 endpoints..."
R2_FILES=$(find . \
  -type f \
  \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" \) \
  ! -path "*/node_modules/*" \
  ! -path "*/.next/*" \
  ! -path "*/.git/*" \
  ! -path "*/archive/*" \
  ! -path "*/docs/*" \
  ! -path "*/scripts/*" \
  -exec grep -l "r2\.cloudflarestorage\.com\|\.r2\.cloudflarestorage\.com" {} \; 2>/dev/null || true)

if [ -n "$R2_FILES" ]; then
  echo "  ⚠️  Found R2 endpoint reference in:"
  while IFS= read -r file; do
    if [ -n "$file" ]; then
      # Check if it's in a comment or example (acceptable)
      if grep -q "r2\.cloudflarestorage\.com" "$file" 2>/dev/null && grep -q "#.*r2\|#.*R2\|example\|Example\|TODO\|FIXME" "$file" 2>/dev/null; then
        echo "     - $file (⚠️  acceptable: comment/example)"
        WARNINGS=$((WARNINGS + 1))
      else
        echo "     - $file"
        ERRORS=$((ERRORS + 1))
      fi
    fi
  done <<< "$R2_FILES"
else
  echo "  ✅ Not found"
fi
echo ""

# Check for hardcoded bucket names (excluding .env files and docs)
echo "Checking for hardcoded bucket names..."
BUCKET_FILES=$(find . \
  -type f \
  \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" \) \
  ! -path "*/node_modules/*" \
  ! -path "*/.next/*" \
  ! -path "*/.git/*" \
  ! -path "*/archive/*" \
  ! -path "*/docs/*" \
  ! -path "*/scripts/*" \
  ! -name ".env*" \
  -exec grep -l "vancelian-dev\|S3_BUCKET.*=.*[\"']" {} \; 2>/dev/null || true)

if [ -n "$BUCKET_FILES" ]; then
  echo "  ⚠️  Found potential hardcoded bucket name in:"
  while IFS= read -r file; do
    if [ -n "$file" ]; then
      echo "     - $file (may be acceptable if in default/example)"
      WARNINGS=$((WARNINGS + 1))
    fi
  done <<< "$BUCKET_FILES"
else
  echo "  ✅ Not found"
fi
echo ""

# Check for hardcoded secrets
echo "Checking for hardcoded secrets..."
SECRET_FOUND=false
for pattern in "${SECRET_PATTERNS[@]}"; do
  SECRET_FILES=$(find . \
    -type f \
    \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" \) \
    ! -path "*/node_modules/*" \
    ! -path "*/.next/*" \
    ! -path "*/.git/*" \
    ! -path "*/archive/*" \
    ! -path "*/docs/*" \
    ! -path "*/scripts/*" \
    ! -name ".env*" \
    ! -name "*.test.*" \
    ! -name "*.spec.*" \
    -exec grep -l "$pattern" {} \; 2>/dev/null || true)
  
  if [ -n "$SECRET_FILES" ]; then
    echo "  ❌ Found potential secret pattern '$pattern' in:"
    while IFS= read -r file; do
      if [ -n "$file" ]; then
        echo "     - $file"
        ERRORS=$((ERRORS + 1))
        SECRET_FOUND=true
      fi
    done <<< "$SECRET_FILES"
  fi
done

if [ "$SECRET_FOUND" = false ]; then
  echo "  ✅ Not found"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  FAIL: $ERRORS"
echo "  WARN: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo "✅ AUDIT PASSED: No hardcode detected"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
elif [ $ERRORS -eq 0 ]; then
  echo "⚠️  AUDIT PASSED WITH WARNINGS: $WARNINGS warning(s) (dev defaults acceptable)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
else
  echo "❌ AUDIT FAILED: $ERRORS error(s), $WARNINGS warning(s)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
fi

