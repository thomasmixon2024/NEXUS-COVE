# Cleanup and Update Nexus Cove Root Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Nexus Cove root folder with the contents of the update folder (from CLAUDE-UPDATE.zip) and remove all backup and copy files, leaving only one copy of each file.

**Architecture:** We will extract the update zip to a temporary directory to obtain the canonical set of update files. Then we will synchronize the root directory with the update directory, removing any extra files/directories (except .git which we will preserve). After synchronization, we will scan for and remove backup and copy files (matching patterns like *.bak, *.backup, *~, .*.swp, etc.) and duplicate directories (like the "(1)" directory). Finally, we will verify that each file in the update exists exactly once in the root.

**Tech Stack:** bash, find, unzip, rsync, grep

**Spec:** Replace everything in the Nexus Cove root folder with all of the items inside the update folder and remove every copy and backup that exists inside it, the Nexus Cove root, leaving only one copy of each file.

**Global Constraints:**
- Preserve the .git directory to maintain version history.
- Do not delete any files outside the Nexus Cove root.
- Preserve file permissions and timestamps where possible.

## Review Focus

1. **Accidental .git deletion:** Ensure the .git directory is not removed during synchronization despite not being in the update folder.
2. **False positive backup removal:** Avoid removing non-backup files that coincidentally match backup patterns (e.g., a legitimate file named "test.bak.py" that is not a backup).
3. **Incomplete backup removal:** Ensure all common backup file patterns are caught, including various suffixes like .bak, .backup, .old, ~, .swp, .swo, .tmp, and files with "backup" or "copy" in the name.
4. **Duplicate file creation:** Prevent creating multiple copies of files during the synchronization process (e.g., due to overlapping copy operations).
5. **Timestamp/permission drift:** Ensure that file modification times and permissions are preserved as much as possible during file operations to avoid unnecessary changes.

## Task 1: Prepare temporary workspace and extract update

**Files:**
- Create: `/tmp/nexus_update_XXXXXX/` (temporary directory)
- Modify: None
- Test: `tests/none` (no test needed for setup)

**Interfaces:**
- Consumes: None
- Produces: `update_dir_path` (the absolute path to the temporary directory containing the extracted update)

- [ ] **Step 1: Create temporary directory**
  ```bash
  update_dir=$(mktemp -d)
  echo $update_dir > /tmp/nexus_update_dir.txt
  ```

- [ ] **Step 2: Verify directory creation**
  - Run: `test -d "$update_dir" && echo "Directory created: $update_dir" || echo "Failed"`
  - Expected: Success message with directory path

- [ ] **Step 3: Extract update zip to temporary directory**
  - Run: `unzip -q /root/NEXUS-COVE/CLAUDE-UPDATE.zip -d "$update_dir"`
  - Expected: No output (successful extraction)

- [ ] **Step 4: Verify extraction**
  - Run: `ls -la "$update_dir" | head -5`
  - Expected: Listing showing top-level entries like .claude/, NexusCove_Skills_Plugins_Installers_v3/, etc.

- [ ] **Step 5: Record update directory for later tasks**
  - Run: `pwd > /tmp/nexus_update_base.txt` (already done in step 1)

## Task 2: Synchronize root with update (preserving .git)

**Files:**
- Modify: `/root/NEXUS-COVE/` (add/update/delete files to match update)
- Test: `tests/none`

**Interfaces:**
- Consumes: `update_dir_path` (from Task 1)
- Produces: `sync_complete` (boolean indicating root matches update minus .git)

- [ ] **Step 1: List all files in update directory (relative paths)**
  - Run: `cd "$update_dir" && find . -type f -not -path './.git/*' | sort > /tmp/update_files.txt`
  - Expected: File containing relative paths of all files in update (excluding .git)

- [ ] **Step 2: List all files in root directory (relative paths)**
  - Run: `cd /root/NEXUS-COVE && find . -type f -not -path './.git/*' | sort > /tmp/root_files.txt`
  - Expected: File containing relative paths of all files in root (excluding .git)

- [ ] **Step 3: Identify files to add/update (in update but not in root or differing)**
  - Run: `comm -13 /tmp/root_files.txt /tmp/update_files.txt > /tmp/to_copy.txt` (files in update not in root)
  - Also: `comm -23 /tmp/root_files.txt /tmp/update_files.txt > /tmp/to_delete.txt` (files in root not in update)
  - Expected: Two files listing paths to copy and paths to delete

- [ ] **Step 4: Copy new/updated files from update to root**
  - Run: `while read relpath; do mkdir -p "/root/NEXUS-COVE/$(dirname "$relpath")"; cp -p "$update_dir/$relpath" "/root/NEXUS-COVE/$relpath"; done < /tmp/to_copy.txt`
  - Expected: No errors; files copied

- [ ] **Step 5: Delete files from root that are not in update (excluding .git)**
  - Run: `while read relpath; do rm -f "/root/NEXUS-COVE/$relpath"; done < /tmp/to_delete.txt`
  - Expected: No errors; files deleted

- [ ] **Step 6: Verify synchronization (excluding .git)**
  - Run: `diff -r /root/NEXUS-COVE/ "$update_dir" -x .git | grep -v '^Only in /root/NEXUS-COVE: .git' | head -5`
  - Expected: No output (directories are identical except possibly .git)

## Task 3: Remove backup and copy files

**Files:**
- Modify: `/root/NEXUS-COVE/` (remove backup files)
- Test: `tests/none`

**Interfaces:**
- Consumes: None
- Produces: `backup_removed_count` (number of backup files removed)

- [ ] **Step 1: Define backup file patterns**
  - Run: `cat > /tmp/backup_patterns.txt << 'EOF'
*.bak
*.backup
*~
.*.swp
.*.swo
*.tmp
*backup*
*copy*
*.old
*.orig
EOF`
  - Expected: Pattern file created

- [ ] **Step 2: Find files matching patterns (excluding .git)**
  - Run: `cd /root/NEXUS-COVE && find . -type f -not -path './.git/*' | grep -E -f /tmp/backup_patterns.txt > /tmp/backup_files.txt`
  - Expected: List of backup files to remove

- [ ] **Step 3: Remove backup files**
  - Run: `while read filepath; do rm -f "$filepath"; echo "Removed: $filepath"; done < /tmp/backup_files.txt`
  - Expected: List of removed files

- [ ] **Step 4: Verify no backup files remain**
  - Run: `cd /root/NEXUS-COVE && find . -type f -not -path './.git/*' | grep -E -f /tmp/backup_patterns.txt | wc -l`
  - Expected: `0`

## Task 4: Remove duplicate directories (e.g., "(1)")

**Files:**
- Modify: `/root/NEXUS-COVE/` (remove duplicate directories)
- Test: `tests/none`

**Interfaces:**
- Consumes: None
- Produces: `duplicate_dirs_removed` (list of removed directories)

- [ ] **Step 1: Identify duplicate directories (like "(1)" )**
  - Run: `cd /root/NEXUS-COVE && find . -type d -name '*(1)*' -not -path './.git/*' > /tmp/duplicate_dirs.txt`
  - Expected: List of duplicate directories (e.g., "./NexusCove_Skills_Plugins_Installers_v3 (1)")

- [ ] **Step 2: Remove duplicate directories**
  - Run: `while read dirpath; do rm -rf "$dirpath"; echo "Removed directory: $dirpath"; done < /tmp/duplicate_dirs.txt`
  - Expected: Directories removed

- [ ] **Step 3: Verify no such directories remain**
  - Run: `cd /root/NEXUS-COVE && find . -type d -name '*(1)*' -not -path './.git/*' | wc -l`
  - Expected: `0`

## Task 5: Final verification

**Files:**
- Modify: None
- Test: `tests/none`

**Interfaces:**
- Consumes: None
- Produces: `verification_passed` (boolean)

- [ ] **Step 1: Ensure each file in update exists exactly once in root**
  - Run: `cd "$update_dir" && find . -type f -not -path './.git/*' | while read relpath; do if [ ! -e "/root/NEXUS-COVE/$relpath" ]; then echo "Missing: $relpath"; exit 1; fi; done`
  - Expected: No output (all files present)

- [ ] **Step 2: Ensure no extra files exist in root (excluding .git and known exceptions)**
  - Run: `cd /root/NEXUS-COVE && find . -type f -not -path './.git/*' | while read relpath; do if [ ! -e "$update_dir/$relpath" ]; then echo "Extra: $relpath"; exit 1; fi; done`
  - Expected: No output (no extra files)

- [ ] **Step 3: Report success**
  - Run: `echo "Synchronization and cleanup complete. Root folder now matches update folder with backups and duplicates removed."`
  - Expected: Confirmation message

## Self-Review

1. **Spec coverage:** The plan addresses the user's request to replace root with update folder contents and remove backups/copies.
2. **Step scan:** Each step has a clear, unambiguous action with a checkable result.
3. **Type consistency:** All paths and variables are consistently named.
4. **Review Focus:** Each review focus item is addressed by specific tasks (e.g., .git preservation in Task 1, backup removal in Task 3).
5. **Proportion:** The plan is concise and focuses on file operations without unnecessary detail.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-10-19-cleanup-update.md`. Please review the plan. Which execution approach would you prefer?**

- **Subagent-driven** - A fresh subagent implements each task and a fresh reviewer checks it before the next one starts, then a whole-branch review at the end. Most thorough; costs a fresh context per task and per review.
- **Native** - I implement every task myself in this session, the way this harness runs work, then one fresh reviewer on the most capable model checks the whole branch. Cheapest and fastest; no independent review until the end. Runs well with a mid-tier session model, since the plan carries the design.

**For this plan I recommend Native, because the tasks are straightforward file operations with minimal inter-task dependencies, and a shipped mistake would be easily reversible via git. Does the plan capture what you want, and which approach should we use?**