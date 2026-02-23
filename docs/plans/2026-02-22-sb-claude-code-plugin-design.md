# Design: Second Brain Claude Code Plugin

**Date:** 2026-02-22
**Status:** Proposed
**Author:** Patrick + Claude

---

## Summary

A Claude Code plugin that provides all second-brain vault operations as namespaced commands (`/sb:*`). Absorbs existing slash commands and adds new interactive commands for creating projects, areas, and people entries with adaptive info-gathering conversations and automatic cross-linking.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Plugin vs commands vs MCP | Plugin | Namespaced commands, skills for conversations, lives in repo |
| UX model | Laptop interactive, VM automated | Clean separation of concerns |
| Project structure depth | Flexible (file → folder) | Start lean, expand when warranted |
| Info-gathering depth | Adaptive (2-3 core, offer more) | User controls depth, always creates something |
| Relationship to existing commands | Absorb and extend | Single source of truth |
| Cross-linking | Automatic | Detect mentions, create/link people stubs |
| Working directory | Anywhere | Discover vault via `VAULT_DIR` env var or `~/second-brain-vault` default |

## Plugin Structure

```
second-brain/
├── .claude-plugin/
│   ├── plugin.json                  # name: "second-brain" → /sb:* namespace
│   ├── commands/
│   │   ├── note.md                  # /sb:note — quick capture to inbox
│   │   ├── triage.md                # /sb:triage — route inbox via PARA
│   │   ├── search.md                # /sb:search — full-text vault search
│   │   ├── daily.md                 # /sb:daily — generate daily summary
│   │   ├── weekly.md                # /sb:weekly — generate weekly summary
│   │   ├── project.md               # /sb:project — NEW: create project
│   │   ├── area.md                  # /sb:area — NEW: create area entry
│   │   └── person.md                # /sb:person — NEW: create person entry
│   └── skills/
│       ├── gather-project/
│       │   └── SKILL.md             # Adaptive project info gathering
│       ├── gather-area/
│       │   └── SKILL.md             # Adaptive area info gathering
│       ├── gather-person/
│       │   └── SKILL.md             # Adaptive person info gathering
│       └── resolve-vault/
│           └── SKILL.md             # Vault path discovery + routes.yaml
```

### plugin.json

```json
{
  "name": "second-brain",
  "description": "Personal knowledge management using PARA methodology",
  "version": "1.0.0",
  "author": "Patrick Jackson"
}
```

## Commands

### Migrated Commands (same behavior, new home)

| Command | Behavior |
|---------|----------|
| `/sb:note <content>` | Create timestamped note in `0_inbox/`, auto-trigger triage |
| `/sb:triage [file\|all]` | Route inbox items via PARA decision tree using `routes.yaml` |
| `/sb:search <query>` | Full-text search across all vault directories |
| `/sb:daily` | Generate daily summary to `_system/summaries/daily/auto/` |
| `/sb:weekly` | Generate weekly summary to `_system/summaries/weekly/auto/` |

### New Commands

| Command | Behavior |
|---------|----------|
| `/sb:project <description>` | Invoke `gather-project` skill, create in `1_projects/active/` |
| `/sb:area <description>` | Invoke `gather-area` skill, create in `2_areas/` |
| `/sb:person <name>` | Invoke `gather-person` skill, create in `5_people/<subgroup>/` |

### New Command Flow

1. Command receives `$ARGUMENTS` (brief description or name)
2. `resolve-vault` skill locates vault and loads `routes.yaml`
3. Command invokes corresponding `gather-*` skill
4. Skill runs adaptive conversation:
   - 2-3 core questions (what, why, first action)
   - Offers to go deeper (goals, people, timeline, dependencies)
   - User can say "that's enough" at any point
5. Skill generates markdown with YAML frontmatter + structured body
6. Skill detects entity mentions → auto-creates stubs in `5_people/`
7. File written to appropriate PARA location

## Skills

### resolve-vault

Model-invoked skill that handles vault discovery:
- Check `VAULT_DIR` env var
- Fall back to `~/second-brain-vault`
- Read and parse `_system/routes.yaml` for allowed values
- Return vault path and routing config to calling command

### gather-project

Adaptive conversation for project creation:

**Core questions (always asked):**
1. What's the goal/outcome of this project?
2. What's the first concrete next action?

**Extended questions (offered, user can skip):**
3. Who's involved? (triggers auto-linking to `5_people/`)
4. What's the timeline or deadline?
5. Any dependencies or blockers?
6. Related areas or resources?

**Output:** Markdown file with frontmatter:

```yaml
---
type: project
status: active
captured_at: ISO-8601
source: claude-code
tags: []
people: []
---
```

**File placement:**
- Single file: `1_projects/active/<slug>.md`
- If user wants more structure: `1_projects/active/<slug>/overview.md` (with optional `tasks.md`, `decisions.md`)

### gather-area

Adaptive conversation for area creation:

**Core questions:**
1. What responsibility or life domain does this cover?
2. What does "healthy" look like for this area?

**Extended:**
3. What are recurring tasks or reviews?
4. Related people?

**Constraint:** Area name must match `routes.yaml` allowed list. If new, skill suggests adding it to `routes.yaml`.

**Output:** `2_areas/<area-name>.md` or `2_areas/<area-name>/overview.md`

### gather-person

Adaptive conversation for person creation:

**Core questions:**
1. How do you know this person? (determines subgroup: family/work/community/vendors)
2. Key context to remember?

**Extended:**
3. Contact info?
4. Related projects or areas?
5. Follow-up items?

**Output:** `5_people/<subgroup>/<name>.md`

## Cross-Linking

When a `gather-*` skill detects a person mention:
1. Search `5_people/` for existing match (fuzzy filename match)
2. If found: add backlink reference in both files
3. If not found: create stub file with minimal frontmatter in appropriate subgroup
4. Stubs are marked with `stub: true` in frontmatter for later enrichment

## Vault Discovery

All commands start with vault resolution:

```
1. Check $VAULT_DIR environment variable
2. Fall back to ~/second-brain-vault
3. Verify directory exists and has expected structure (0_inbox/, _system/, etc.)
4. Load _system/routes.yaml for routing config
5. If vault not found → clear error message with setup instructions
```

## Compatibility

- **Existing vault content:** Fully compatible. New commands create files in the same PARA structure with the same frontmatter schema.
- **Existing automation:** Unaffected. Inbox watcher, daily/weekly timers continue to work.
- **Triage agent:** Compatible. Files created by `/sb:project` skip triage (already placed). Files from `/sb:note` still go through triage as before.
- **install.sh:** Step 6 updated to deploy from `.claude-plugin/commands/` instead of `.claude/commands/`. Old `.claude/commands/` directory retired.
- **Syncthing:** No impact. Plugin lives in the repo, not the vault.

## Migration

1. Move `.claude/commands/*.md` → `.claude-plugin/commands/`
2. Update `install.sh` to deploy from new location
3. Remove old `.claude/commands/` directory
4. No vault changes needed

## What This Does NOT Include

- No MCP server or custom tooling
- No changes to the PydanticAI triage agent
- No UI or web interface
- No changes to Syncthing or sync topology
- No changes to systemd services or automation scripts
