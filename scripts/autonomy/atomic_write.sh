#!/bin/bash
# atomic_write.sh — canonical implementation of the Atomic Write Protocol
# Usage: atomic_write.sh <target-path> <content-file>
set -euo pipefail
G=$'\033[92m'; R=$'\033[91m'; Y=$'\033[93m'
C=$'\033[96m'; M=$'\033[35m'; B=$'\033[1m'; N=$'\033[0m'

TARGET="${1:?usage: atomic_write.sh <target> <content>}"
SRC="${2:?usage: atomic_write.sh <target> <content>}"
TMP="$(mktemp)"

printf "${B}${C}▶ PHASE 1/4 BACKUP${N}\n"
[ -f "$TARGET" ] && { cp "$TARGET" "${TARGET}.bak-$(date +%Y%m%dT%H%M%SZ)"; printf "  ${G}✓${N} backup\n"; } || printf "  ${Y}⚠${N} no existing file to back up\n"

printf "${B}${C}▶ PHASE 2/4 WRITE to temp${N}\n"
cp "$SRC" "$TMP"
[ -s "$TMP" ] && printf "  ${G}✓${N} %s bytes\n" "$(wc -c < "$TMP")" || { printf "  ${R}✗${N} empty\n"; exit 1; }

printf "${B}${C}▶ PHASE 3/4 VALIDATE${N}\n"
case "$TARGET" in
  *.json) jq . "$TMP" > /dev/null && printf "  ${G}✓${N} json valid\n" || { printf "  ${R}✗${N} json invalid\n"; exit 1; } ;;
  *.py)   python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$TMP" && printf "  ${G}✓${N} python valid\n" || { printf "  ${R}✗${N} python invalid\n"; exit 1; } ;;
  *.sh)   bash -n "$TMP" && printf "  ${G}✓${N} shell valid\n" || { printf "  ${R}✗${N} shell invalid\n"; exit 1; } ;;
  *)      [ -s "$TMP" ] && printf "  ${G}✓${N} non-empty\n" || exit 1 ;;
esac

printf "${B}${C}▶ PHASE 4/4 PROMPT + COMMIT${N}\n"
printf "${Y}Overwrite %s? [y/N] ${N}" "$TARGET"
read -r a
case "$a" in
  y|Y) mv "$TMP" "$TARGET"; chmod 644 "$TARGET"; printf "  ${G}✓${N} installed\n" ;;
  *)   printf "  ${Y}⚠${N} aborted — temp kept at %s\n" "$TMP"; exit 2 ;;
esac

printf "\n${B}${M}SUMMARY${N}\n"
printf "  ${G}STATUS: SUCCESS${N}\n"
printf "  FILE:   %s\n" "$TARGET"
printf "  SIZE:   %s bytes\n" "$(wc -c < "$TARGET")"
