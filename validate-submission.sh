#!/bin/bash

# OpenEnv Submission Validator
# Usage: ./validate-submission.sh <HF_SPACE_URL> <PROJECT_DIR>

URL=$1
DIR=$2

if [ -z "$URL" ] || [ -z "$DIR" ]; then
    echo "Usage: ./validate-submission.sh <HF_SPACE_URL> <PROJECT_DIR>"
    exit 1
fi

echo "--- Starting Validation ---"

# 1. Checking Connection
echo "[1/3] Checking Ping to $URL..."
HTTP_STATUS=$(curl -o /dev/null -s -w "%{http_code}" "$URL")
if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 302 ]; then
    echo "✅ URL is reachable (Status: $HTTP_STATUS)"
else
    echo "❌ URL unreachable. Status: $HTTP_STATUS"
    exit 1
fi

# 2. Checking File Structure
echo "[2/3] Checking Project Structure in $DIR..."
REQUIRED_FILES=("app.py" "Dockerfile" "openenv.yaml" "requirements.txt")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$DIR/$file" ]; then
        echo "✅ Found $file"
    else
        echo "❌ Missing $file"
        exit 1
    fi
done

# 3. Validating openenv.yaml
echo "[3/3] Validating openenv.yaml..."
if grep -q "name:" "$DIR/openenv.yaml" && grep -q "tasks:" "$DIR/openenv.yaml"; then
    echo "✅ openenv.yaml looks valid."
else
    echo "❌ openenv.yaml is missing required fields (name or tasks)."
    exit 1
fi

echo "--- All 3/3 checks passed! ---"
echo "You are ready to submit your URL: $URL"