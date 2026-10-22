#!/usr/bin/env bash
# Nexus Cove Inventory Session — Handoff Script
# Generated: 2026-10-21 08:26 UTC
# Run this script to resume the inventory task from where it left off.

set -euo pipefail

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  NEXUS COVE INVENTORY — SESSION HANDOFF                       ║"
echo "║  Task: Read-only inventory of Nexus Cove files across 3 envs  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Search Roots Confirmed ──────────────────────────────────────
echo "✅ Search roots confirmed:"
echo "   Termux:       /data/data/com.termux/files/home"
echo "   Ubuntu /root: /root"
echo "   Ubuntu /home: /home"
echo "   Android /sdcard: /sdcard"
echo "   Android Download: /storage/emulated/0/Download"
echo "   Android Documents: /storage/emulated/0/Documents"
echo ""

# ── What Was Completed ──────────────────────────────────────────
echo "✅ Completed enumerations:"
echo ""
echo "   Termux (/data/data/com.termux/files/home):"
find /data/data/com.termux/files/home -maxdepth 6 \( -iname "*nexus*cove*" -o -iname "*nexuscove*" \) 2>/dev/null | sed 's/^/      /'
echo ""
echo "   Ubuntu /root:"
find /root -maxdepth 6 \( -iname "*nexus*cove*" -o -iname "*nexuscove*" \) 2>/dev/null | head -30 | sed 's/^/      /'
echo "      ... (40+ total matches, truncated)"
echo ""
echo "   Ubuntu /home/ubuntu:"
find /home -maxdepth 6 \( -iname "*nexus*cove*" -o -iname "*nexuscove*" \) 2>/dev/null | sed 's/^/      /'
echo ""

# ── What Remains (Rate-Limited) ─────────────────────────────────
echo "⏳ Pending (rate-limited on Android roots):"
echo "   /sdcard"
echo "   /storage/emulated/0/Download"
echo "   /storage/emulated/0/Documents"
echo ""

# ── Git Repo Identification ─────────────────────────────────────
echo "🔍 Git repos with NEXUS-COVE remote:"
for repo in /data/data/com.termux/files/home/NEXUS-COVE /root/NEXUS-COVE; do
  if [ -d "$repo/.git" ]; then
    url=$(git -C "$repo" remote get-url origin 2>/dev/null || echo "none")
    branch=$(git -C "$repo" branch --show-current 2>/dev/null || echo "unknown")
    head=$(git -C "$repo" rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "unknown")
    echo "   $repo"
    echo "      origin: $url"
    echo "      branch: $branch @ $head"
  fi
done
echo ""

# ── Credential Files ────────────────────────────────────────────
echo "🔐 Credential files (path + fingerprint only):"
for key in /data/data/com.termux/files/home/.ssh/id_ed25519.pub /root/.ssh/id_ed25519.pub; do
  if [ -f "$key" ]; then
    fp=$(ssh-keygen -lf "$key" 2>/dev/null | awk '{print $2}')
    echo "   $key → $fp"
  fi
done
echo ""

# ── Next Commands to Run ────────────────────────────────────────
echo "📋 Next commands to complete inventory:"
echo ""
echo "   # Android roots (retry after rate limit clears):"
echo "   find /sdcard -maxdepth 6 \\( -iname \"*nexus*cove*\" -o -iname \"*nexuscove*\" \\) 2>/dev/null"
echo "   find /storage/emulated/0/Download -maxdepth 6 \\( -iname \"*nexus*cove*\" -o -iname \"*nexuscove*\" \\) 2>/dev/null"
echo "   find /storage/emulated/0/Documents -maxdepth 6 \\( -iname \"*nexus*cove*\" -o -iname \"*nexuscove*\" \\) 2>/dev/null"
echo ""
echo "   # Git repo identification (all roots):"
echo "   for root in /data/data/com.termux/files/home /root /home /sdcard /storage/emulated/0/Download /storage/emulated/0/Documents; do"
echo "     find \"\$root\" -maxdepth 6 -name \".git\" -type d 2>/dev/null | while read g; do"
echo "       repo=\$(dirname \"\$g\")"
echo "       url=\$(git -C \"\$repo\" remote get-url origin 2>/dev/null)"
echo "       case \"\$url\" in *NEXUS-COVE*) echo \"\$repo|\$url\";; esac"
echo "     done"
echo "   done"
echo ""
echo "   # Repo status details:"
echo "   for repo in /data/data/com.termux/files/home/NEXUS-COVE /root/NEXUS-COVE; do"
echo "     echo \"=== \$repo ===\""
echo "     git -C \"\$repo\" log origin/main..HEAD --oneline 2>/dev/null | head -5"
echo "     git -C \"\$repo\" status --short"
echo "     git -C \"\$repo\" branch -a"
echo "   done"
echo ""

# ── Output Target ───────────────────────────────────────────────
echo "📝 Report output: /storage/emulated/0/Documents/nexus-cove-inventory.md"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Checkpoint saved: cp_20261021_082617 (manual)"
echo "Session complete — run this script to resume."
echo "═══════════════════════════════════════════════════════════════"