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
echo -e "${CYAN}STEP 1  ›  INJECT APPLICATION FAILURE${RESET}"
echo -e "${DIM}────────────────────────────────────────────────────────────${RESET}"
echo
echo -e "Injecting deliberate configuration fault..."
echo

aws lambda update-function-configuration \
  --function-name task-app \
  --environment 'Variables={TABLE_NAME=appdata-wrong}' \
  --region ap-southeast-1 \
  > /dev/null

if [ $? -eq 0 ]; then
    echo -e "${WHITE}Lambda function${RESET}     task-app"
    echo -e "${WHITE}Configuration${RESET}       TABLE_NAME"
    echo -e "${WHITE}Injected value${RESET}      ${RED}appdata-wrong${RESET}"
    echo
    echo -e "${RED}✗  FAULT INJECTED${RESET}"
    echo
    echo -e "${YELLOW}Application is now expected to fail.${RESET}"
else
    echo -e "${RED}✗  FAILED TO INJECT FAULT${RESET}"
    exit 1
fi

echo
