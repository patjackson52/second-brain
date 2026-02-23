# Second Brain Claude Code Plugin — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Claude Code plugin that absorbs existing slash commands into `/sb:*` namespace and adds new interactive commands for projects, areas, and people.

**Architecture:** A `.claude-plugin/` directory in the repo root with `plugin.json`, `commands/` (8 command files), and `skills/` (4 skill directories). Existing `.claude/commands/` migrated into the plugin. `install.sh` updated to deploy from the new location.

**Tech Stack:** Claude Code plugin system (plugin.json + commands/*.md + skills/*/SKILL.md), Bash (install.sh), Markdown/YAML

---

### Task 1: Scaffold Plugin Structure

**Files:**
- Create: `.claude-plugin/plugin.json`

**Step 1: Create plugin.json**

```json
{
  "name": "second-brain",
  "description": "Personal knowledge management using PARA methodology",
  "version": "1.0.0",
  "author": {
    "name": "Patrick Jackson"
  }
}
```

**Step 2: Verify directory structure**

Run: `ls .claude-plugin/`
Expected: `plugin.json`

**Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat: scaffold claude code plugin with plugin.json"
```

---

### Task 2: Migrate Existing Commands

Move all 5 existing commands from `.claude/commands/` into `.claude-plugin/commands/`, adding frontmatter metadata to each.

**Files:**
- Create: `.claude-plugin/commands/note.md`
- Create: `.claude-plugin/commands/triage.md`
- Create: `.claude-plugin/commands/search.md`
- Create: `.claude-plugin/commands/daily.md`
- Create: `.claude-plugin/commands/weekly.md`

**Step 1: Copy and add frontmatter to note.md**

Add this frontmatter block to the top of the existing content:

```yaml
---
description: Create a new note in the inbox from quick capture
argument-hint: <content to capture>
allowed-tools: [Read, Write, Bash, Glob, Grep]
---
```

Prepend vault discovery to the instructions:

```markdown
## Vault Discovery

1. Check `$VAULT_DIR` environment variable for vault path
2. If not set, use `~/second-brain-vault`
3. Verify the vault exists by checking for `0_inbox/` directory
```

Rest of the content is identical to `.claude/commands/note.md`.

**Step 2: Copy and add frontmatter to triage.md**

```yaml
---
description: Classify and route inbox notes using PARA methodology
argument-hint: [file path | all]
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---
```

Prepend the same vault discovery block. Rest identical to existing.

**Step 3: Copy and add frontmatter to search.md**

```yaml
---
description: Full-text search across the entire knowledge base
argument-hint: <search query>
allowed-tools: [Read, Glob, Grep]
---
```

Prepend vault discovery. Rest identical.

**Step 4: Copy and add frontmatter to daily.md**

```yaml
---
description: Generate a daily summary of vault activity
argument-hint: [date in YYYY-MM-DD format]
allowed-tools: [Read, Write, Bash, Glob, Grep]
---
```

Prepend vault discovery. Rest identical.

**Step 5: Copy and add frontmatter to weekly.md**

```yaml
---
description: Generate a weekly summary of vault activity
argument-hint: [week in YYYY-Www format]
allowed-tools: [Read, Write, Bash, Glob, Grep]
---
```

Prepend vault discovery. Rest identical.

**Step 6: Verify all commands copied**

Run: `ls .claude-plugin/commands/`
Expected: `daily.md  note.md  search.md  triage.md  weekly.md`

**Step 7: Commit**

```bash
git add .claude-plugin/commands/
git commit -m "feat: migrate existing commands into plugin with frontmatter"
```

---

### Task 3: Create resolve-vault Skill

This skill is model-invoked — Claude uses it automatically when a command needs vault access.

**Files:**
- Create: `.claude-plugin/skills/resolve-vault/SKILL.md`

**Step 1: Write the skill**

```markdown
---
name: resolve-vault
description: Discover the second-brain vault path and load routing configuration. Use whenever a command needs to read or write vault files.
tools: Read, Glob, Bash
user-invocable: false
---

# Resolve Vault

Locate the second-brain vault directory and load its routing configuration.

## Resolution Steps

1. Check `$VAULT_DIR` environment variable
2. If not set, default to `~/second-brain-vault`
3. Verify the directory exists and contains expected structure:
   - `0_inbox/` directory exists
   - `_system/` directory exists
   - `_system/routes.yaml` file exists
4. If vault not found, tell the user:
   - "Could not find second-brain vault. Set VAULT_DIR or run setup-vault.sh"
5. Read and parse `_system/routes.yaml`
6. Return vault path and routing config to the calling context

## What to Extract from routes.yaml

- `folders.*` — directory name mappings
- `areas.allowed` — list of valid area names
- `resources.allowed` — list of valid resource names
- `people.groups` — list of people subgroups (family, work, community, vendors)
- `uncertainty.keep_in_inbox_below_confidence` — confidence threshold (0.7)
- `hints.*` — keyword hints for classification
- `structure.projects.*` — project subfolder conventions
```

**Step 2: Verify**

Run: `ls .claude-plugin/skills/resolve-vault/`
Expected: `SKILL.md`

**Step 3: Commit**

```bash
git add .claude-plugin/skills/resolve-vault/
git commit -m "feat: add resolve-vault skill for vault discovery"
```

---

### Task 4: Create gather-project Skill

**Files:**
- Create: `.claude-plugin/skills/gather-project/SKILL.md`

**Step 1: Write the skill**

```markdown
---
name: gather-project
description: Adaptive conversation to gather project details and create a structured project entry. Use when the user invokes /sb:project.
tools: Read, Write, Bash, Glob, Grep
---

# Gather Project Info

Run an adaptive conversation to create a new project in the vault.

## Prerequisites

Use the resolve-vault skill first to locate the vault and load routes.yaml.

## Core Questions (always ask)

1. **Goal:** "What's the goal or outcome of this project? What does 'done' look like?"
2. **Next action:** "What's the first concrete next step?"

After these two, ask:

"Want me to capture more detail (people involved, timeline, dependencies), or is this enough to get started?"

## Extended Questions (if user wants more)

3. **People:** "Who's involved?" — Note names for cross-linking
4. **Timeline:** "Any deadline or target date?"
5. **Dependencies:** "Anything blocking this or that this depends on?"
6. **Related:** "Related areas or existing resources in the vault?"

The user can say "that's enough" at any point.

## Output

### File Location

Default: `{vault}/1_projects/active/{slug}.md`

If the user asks for more structure:
```
{vault}/1_projects/active/{slug}/
├── index.md        (main project file)
├── tasks.md        (task tracking)
└── decisions.md    (decision log)
```

### Frontmatter

```yaml
---
type: project
status: active
captured_at: {ISO-8601 timestamp}
source: claude-code
tags: [{derived from conversation}]
people: [{names mentioned}]
ai_generated: false
---
```

### Body Structure

```markdown
# {Project Title}

## Goal
{from question 1}

## Next Actions
- [ ] {from question 2}

## Context
{any additional detail from extended questions}

## People
{if mentioned — link to 5_people/ entries}

## Timeline
{if provided}
```

### Slug Generation

- Lowercase, hyphens, max 5 words
- Derived from the project title/goal
- Example: "buy-recteq-smoker", "kitchen-renovation"

## Cross-Linking

After creating the project file, check for people mentions:

1. For each person name mentioned:
   - Search `{vault}/5_people/` for existing file matching the name
   - If found: add a `## Related Projects` link in the person file
   - If not found: create a stub at `{vault}/5_people/work/{name-slug}.md`:

```yaml
---
type: person
stub: true
captured_at: {timestamp}
source: claude-code
ai_generated: false
---

# {Person Name}

_Stub created from project: {project-name}_
```

2. Add the person filename to the project's `people:` frontmatter list
```

**Step 2: Verify**

Run: `ls .claude-plugin/skills/gather-project/`
Expected: `SKILL.md`

**Step 3: Commit**

```bash
git add .claude-plugin/skills/gather-project/
git commit -m "feat: add gather-project skill for adaptive project creation"
```

---

### Task 5: Create gather-area Skill

**Files:**
- Create: `.claude-plugin/skills/gather-area/SKILL.md`

**Step 1: Write the skill**

```markdown
---
name: gather-area
description: Adaptive conversation to gather area-of-responsibility details and create an area entry. Use when the user invokes /sb:area.
tools: Read, Write, Bash, Glob, Grep
---

# Gather Area Info

Run an adaptive conversation to create a new area entry in the vault.

## Prerequisites

Use the resolve-vault skill first to locate the vault and load routes.yaml.

## Area Name Validation

The area name MUST match one of the allowed names from `routes.yaml` `areas.allowed`:
- Health, Family, Home, Finance, Work, Learning, Community

If the user's description doesn't match an existing area, ask:
"The closest existing area is '{closest}'. Should I use that, or would you like to add '{new-name}' to the allowed areas list?"

If adding a new area, append it to `_system/routes.yaml` under `areas.allowed`.

## Core Questions (always ask)

1. **Domain:** "What responsibility or life domain does this cover?"
2. **Healthy state:** "What does 'healthy' look like for this area? How do you know it's going well?"

Then ask: "Want to add more detail (recurring tasks, related people), or is this enough?"

## Extended Questions (if user wants more)

3. **Recurring:** "Any recurring tasks or regular reviews for this area?"
4. **People:** "Key people connected to this area?"

## Output

### File Location

`{vault}/2_areas/{AreaName}.md`

If the area needs sub-structure: `{vault}/2_areas/{AreaName}/overview.md`

### Frontmatter

```yaml
---
type: area
status: active
captured_at: {ISO-8601 timestamp}
source: claude-code
tags: [{derived}]
ai_generated: false
---
```

### Body Structure

```markdown
# {Area Name}

## What This Covers
{from question 1}

## Healthy State
{from question 2}

## Recurring Tasks
{if provided}

## Related People
{if mentioned — link to 5_people/ entries}
```

## Cross-Linking

Same as gather-project: detect people mentions, create stubs if needed.
```

**Step 2: Verify**

Run: `ls .claude-plugin/skills/gather-area/`
Expected: `SKILL.md`

**Step 3: Commit**

```bash
git add .claude-plugin/skills/gather-area/
git commit -m "feat: add gather-area skill for adaptive area creation"
```

---

### Task 6: Create gather-person Skill

**Files:**
- Create: `.claude-plugin/skills/gather-person/SKILL.md`

**Step 1: Write the skill**

```markdown
---
name: gather-person
description: Adaptive conversation to gather person details and create a people entry. Use when the user invokes /sb:person.
tools: Read, Write, Bash, Glob, Grep
---

# Gather Person Info

Run an adaptive conversation to create a new person entry in the vault.

## Prerequisites

Use the resolve-vault skill first to locate the vault and load routes.yaml.

## Core Questions (always ask)

1. **Relationship:** "How do you know {name}?" — Determines subgroup:
   - Family → `5_people/family/`
   - Colleague/work → `5_people/work/`
   - Friend/neighbor/community → `5_people/community/`
   - Service provider/business → `5_people/vendors/`
2. **Context:** "What's the key context to remember about {name}?"

Then ask: "Want to add more (contact info, related projects, follow-ups), or is this enough?"

## Extended Questions (if user wants more)

3. **Contact:** "Any contact info to store? (email, phone, etc.)"
4. **Related:** "Any active projects or areas connected to {name}?"
5. **Follow-ups:** "Any pending follow-up items with {name}?"

## Output

### File Location

`{vault}/5_people/{subgroup}/{name-slug}.md`

### Frontmatter

```yaml
---
type: person
relationship: {family|work|community|vendor}
captured_at: {ISO-8601 timestamp}
source: claude-code
tags: [{derived}]
ai_generated: false
---
```

### Body Structure

```markdown
# {Person Name}

## Context
{from question 2}

## Contact
{if provided}

## Related Projects
{if mentioned — link to 1_projects/ entries}

## Related Areas
{if mentioned — link to 2_areas/ entries}

## Follow-ups
{if provided}
- [ ] {follow-up items}
```

## Cross-Linking

If the user mentions projects or areas:
1. Search vault for matching project/area files
2. If found: add backlink to the person in the project/area file's `## People` section
```

**Step 2: Verify**

Run: `ls .claude-plugin/skills/gather-person/`
Expected: `SKILL.md`

**Step 3: Commit**

```bash
git add .claude-plugin/skills/gather-person/
git commit -m "feat: add gather-person skill for adaptive people entry creation"
```

---

### Task 7: Create New Commands (project, area, person)

**Files:**
- Create: `.claude-plugin/commands/project.md`
- Create: `.claude-plugin/commands/area.md`
- Create: `.claude-plugin/commands/person.md`

**Step 1: Write project.md**

```markdown
---
description: Create a new project with guided info gathering
argument-hint: <brief project description>
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# Create Project

Create a new project entry in the second-brain vault using adaptive info gathering.

## Instructions

1. Locate the vault using the resolve-vault skill
2. Use the gather-project skill to run an adaptive conversation with the user
3. The user provided this initial description: $ARGUMENTS
4. Pass the description to the gather-project skill as starting context — use it to pre-fill what you can and skip questions already answered by the description

If `$ARGUMENTS` is empty, start the conversation from scratch.
```

**Step 2: Write area.md**

```markdown
---
description: Create a new area-of-responsibility entry with guided info gathering
argument-hint: <area name or description>
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# Create Area

Create a new area entry in the second-brain vault using adaptive info gathering.

## Instructions

1. Locate the vault using the resolve-vault skill
2. Use the gather-area skill to run an adaptive conversation with the user
3. The user provided this initial description: $ARGUMENTS
4. Pass the description to the gather-area skill as starting context — validate against routes.yaml allowed areas

If `$ARGUMENTS` is empty, start the conversation from scratch.
```

**Step 3: Write person.md**

```markdown
---
description: Create a new person entry with guided info gathering
argument-hint: <person name>
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# Create Person

Create a new person entry in the second-brain vault using adaptive info gathering.

## Instructions

1. Locate the vault using the resolve-vault skill
2. Use the gather-person skill to run an adaptive conversation with the user
3. The user provided this name/description: $ARGUMENTS
4. Pass the name to the gather-person skill as the person's name

If `$ARGUMENTS` is empty, ask for the person's name first.
```

**Step 4: Verify all commands**

Run: `ls .claude-plugin/commands/`
Expected: `area.md  daily.md  note.md  person.md  project.md  search.md  triage.md  weekly.md`

**Step 5: Commit**

```bash
git add .claude-plugin/commands/project.md .claude-plugin/commands/area.md .claude-plugin/commands/person.md
git commit -m "feat: add project, area, and person commands"
```

---

### Task 8: Update install.sh to Deploy from Plugin

**Files:**
- Modify: `install.sh` (step 6 section, around lines 247-268)

**Step 1: Update the source path and command list**

Change:
```bash
COMMANDS_DIR="$DATA_DIR/claude/commands"
mkdir -p "$COMMANDS_DIR"

COMMANDS=(
  "note.md"
  "triage.md"
  "search.md"
  "daily.md"
  "weekly.md"
)

for cmd in "${COMMANDS[@]}"; do
  src="$REPO_DIR/.claude/commands/$cmd"
```

To:
```bash
COMMANDS_DIR="$DATA_DIR/claude/commands"
mkdir -p "$COMMANDS_DIR"

COMMANDS=(
  "note.md"
  "triage.md"
  "search.md"
  "daily.md"
  "weekly.md"
  "project.md"
  "area.md"
  "person.md"
)

for cmd in "${COMMANDS[@]}"; do
  src="$REPO_DIR/.claude-plugin/commands/$cmd"
```

**Step 2: Verify syntax**

Run: `bash -n install.sh`
Expected: no output (success)

**Step 3: Commit**

```bash
git add install.sh
git commit -m "fix: deploy commands from .claude-plugin/ and add new commands"
```

---

### Task 9: Remove Old .claude/commands/ Directory

**Files:**
- Delete: `.claude/commands/note.md`
- Delete: `.claude/commands/triage.md`
- Delete: `.claude/commands/search.md`
- Delete: `.claude/commands/daily.md`
- Delete: `.claude/commands/weekly.md`

**Step 1: Remove old command files**

```bash
git rm -r .claude/commands/
```

**Step 2: Verify plugin commands still present**

Run: `ls .claude-plugin/commands/`
Expected: all 8 command files

**Step 3: Commit**

```bash
git commit -m "chore: remove old .claude/commands/ (migrated to plugin)"
```

---

### Task 10: End-to-End Smoke Test

**Step 1: Verify plugin is recognized**

Run Claude Code from the repo directory and check that `/sb:` commands appear:

```bash
claude --print "List all available slash commands that start with /sb:"
```

Expected: Should list `/sb:note`, `/sb:triage`, `/sb:search`, `/sb:daily`, `/sb:weekly`, `/sb:project`, `/sb:area`, `/sb:person`

**Step 2: Test /sb:note**

```bash
claude --print "/sb:note Test note from plugin smoke test"
```

Expected: File created in `~/second-brain-vault/0_inbox/` with correct frontmatter

**Step 3: Test /sb:search**

```bash
claude --print "/sb:search smoke test"
```

Expected: Finds the note just created

**Step 4: Test /sb:project interactively**

```bash
claude "/sb:project Build a treehouse for the kids"
```

Expected: Adaptive conversation starts, asks about goals and next actions

**Step 5: Verify vault structure unchanged**

```bash
ls ~/second-brain-vault/
```

Expected: Same PARA directories, no new dotfiles

**Step 6: Commit any test cleanup**

```bash
# Remove test files if created
git status
```

---

### Task 11: Deploy to VM

**Step 1: Push changes**

```bash
git push origin feature/sb-plugin-design
```

**Step 2: Merge PR and pull on VM**

```bash
# After PR merge:
ssh ubuntu@<VM_IP> 'cd ~/second-brain && git pull && sudo ./install.sh'
```

**Step 3: Verify commands deployed on VM**

```bash
ssh ubuntu@<VM_IP> 'ls ~/.second-brain/claude/commands/'
```

Expected: All 8 command files present

**Step 4: Final commit**

```bash
git commit -m "chore: verified plugin deployment on VM"
```
