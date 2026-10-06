#!/bin/bash

# Colours
BLUE='\033[1;34m'
CYAN='\033[1;36m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
DIM='\033[2m'
RESET='\033[0m'

clear

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗"
echo -e "║              AI APPLICATION TROUBLESHOOTER              ║"
echo -e "╚══════════════════════════════════════════════════════════╝${RESET}"
echo
echo -e "${CYAN}STEP 3  ›  HUMAN-APPROVED REMEDIATION${RESET}"
echo -e "${DIM}────────────────────────────────────────────────────────────${RESET}"
echo
echo -e "${YELLOW}Human approval received.${RESET}"
echo -e "Executing agent remediation..."
echo

aws lambda invoke \
  --function-name ai-troubleshooter \
  --payload '{"approved":true}' \
  --cli-binary-format raw-in-base64-out \
  --region ap-southeast-1 \
  response.json > /dev/null

python3 - <<'PY'
import json

with open("response.json") as f:
    outer = json.load(f)

result = json.loads(outer["body"])

remediation = result["remediation"]
verification = result["verification"]
app = result["application_verification"]

GREEN = "\033[1;32m"
RED = "\033[1;31m"
WHITE = "\033[1;37m"
DIM = "\033[2m"
RESET = "\033[0m"

print(f"{WHITE}REMEDIATION PERFORMED{RESET}")
print(f"{DIM}────────────────────────────────────────────────────────────{RESET}")
print(f"Function        {remediation['function_name']}")
print(f"TABLE_NAME      {remediation['TABLE_NAME']}")

print()
print(f"{WHITE}CONFIGURATION VERIFICATION{RESET}")
print(f"{DIM}────────────────────────────────────────────────────────────{RESET}")

if verification["verified"]:
    print(f"{GREEN}✓  Configuration verified{RESET}")
else:
    print(f"{RED}✗  Configuration verification failed{RESET}")

print(f"Expected        {verification['expected_TABLE_NAME']}")
print(f"Actual          {verification['actual_TABLE_NAME']}")
print(f"AWS status      {verification['update_status']}")

print()
print(f"{WHITE}APPLICATION VERIFICATION{RESET}")
print(f"{DIM}────────────────────────────────────────────────────────────{RESET}")

if app["verified"]:
    print(f"{GREEN}✓  Application test passed{RESET}")
else:
    print(f"{RED}✗  Application test failed{RESET}")

print(f"HTTP status     {app['application_status_code']}")

print()
print(f"{DIM}────────────────────────────────────────────────────────────{RESET}")

if app["verified"]:
    print()
    print(f"{GREEN}✓  SERVICE RESTORED{RESET}")
else:
    print()
    print(f"{RED}✗  REMEDIATION FAILED{RESET}")
PY

echo
