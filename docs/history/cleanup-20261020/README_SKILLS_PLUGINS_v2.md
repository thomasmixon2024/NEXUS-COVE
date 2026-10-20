# Nexus Cove Skills & Plugins Installers (v2)

Four separate bash setup scripts matching the Required / Optional grouping:

1. **01_setup_required_skills.sh**
   - general-purpose, Plan, code-review, simplify

2. **02_setup_required_plugins.sh**
   - superpowers@claude-plugins-official

3. **03_setup_optional_skills.sh**
   - Explore, fewer-permission-prompts, loop, workflow-authoring, update-config

4. **04_setup_optional_plugins.sh**
   - Currently none (documents that fact)

## Recommended Order
1 → 2 → 3 → 4

Each script:
- Creates a local Logs/ directory and writes a timestamped log
- Emits green Success / red Failure messages
- Prints purple next-step suggestions and brighter-purple resolution commands
- Generates human-readable Markdown docs + JSON settings snippets

Extract the zip, then:
```bash
chmod +x *.sh
./01_setup_required_skills.sh
./02_setup_required_plugins.sh
./03_setup_optional_skills.sh
./04_setup_optional_plugins.sh
```
