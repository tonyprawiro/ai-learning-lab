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
echo -e "${CYAN}STEP 2  ›  AI AGENT INVESTIGATION${RESET}"
echo -e "${DIM}────────────────────────────────────────────────────────────${RESET}"
echo
echo -e "Invoking troubleshooting agent..."
echo

aws lambda invoke \
  --function-name ai-troubleshooter \
  --payload '{"approved":false}' \
  --cli-binary-format raw-in-base64-out \
  --region ap-southeast-1 \
  response.json > /dev/null

python3 - <<'PY'
import json

with open("response.json") as f:
    outer = json.load(f)

result = json.loads(outer["body"])
diagnosis = result["diagnosis"]

GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
WHITE = "\033[1;37m"
DIM = "\033[2m"
RESET = "\033[0m"

print(f"{GREEN}✓  ROOT CAUSE IDENTIFIED{RESET}")
print()
print(f"{WHITE}AGENT DIAGNOSIS{RESET}")
print(f"{DIM}────────────────────────────────────────────────────────────{RESET}")
print(diagnosis["root_cause"])

print()
print(f"{WHITE}PROPOSED REMEDIATION{RESET}")
print(f"{DIM}────────────────────────────────────────────────────────────{RESET}")

proposal = diagnosis["proposed_remediation"]

print(f"Action          {proposal['action']}")
print(f"Function        {proposal['function']}")
print(f"Configuration   {proposal['environment_variable']}")
print(f"Current value   {proposal['current_value']}")
print(f"Proposed value  {proposal['proposed_value']}")

print()
print(f"{YELLOW}⚠  HUMAN APPROVAL REQUIRED{RESET}")
print()
print("No remediation has been performed.")
PY

echo
