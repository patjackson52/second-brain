Classify and route notes from the inbox using the PARA methodology.

## References
- Routing config: `_system/routes.yaml`
- Decision tree: `_system/prompts/triage_para.md`
- File ops rules: `_system/file_ops_contract.md`

## Instructions

### Input
- If `$ARGUMENTS` is a specific file path: classify only that file
- If `$ARGUMENTS` is "all" or empty: process all files in `0_inbox/` (excluding .gitkeep)

### Setup
1. Read `_system/routes.yaml` for folder names, allowed area/resource names, keyword hints, and confidence thresholds.
2. Read `_system/file_ops_contract.md` for safety rules.

### PARA Classification

For each inbox file, read its content and walk the PARA decision tree **in strict order**:

| Question | If yes → | Destination |
|----------|----------|-------------|
| Q1: Tied to a specific outcome with a deadline or finishable deliverable? | **PROJECT** | `1_projects/active/<slug>/` |
| Q2: Ongoing responsibility/role/standard with no end date? | **AREA** | `2_areas/<area-name>/` |
| Q3: Reference material or topic of interest, no commitment? | **RESOURCE** | `3_resources/<resource-name>/` |
| Q4: Inactive, completed, obsolete, or purely historical? | **ARCHIVE** | `4_archive/` |
| Q5: None of the above confidently applies | **INBOX** | Keep in `0_inbox/`, mark `needs_triage: true` |

**People handling:** If the note is primarily about a person or relationship, route to `5_people/` regardless of PARA category. Use subgroups from routes.yaml (family/work/community/vendors) if clearly applicable.

Use `areas.allowed` and `resources.allowed` from routes.yaml to pick the best subfolder name. Use `hints` keywords to raise confidence but always follow the decision tree.

### Confidence & Routing

- **High confidence (>= 0.7):** Move file to destination, update frontmatter.
- **Low confidence (< 0.7):** Keep in `0_inbox/` and add `needs_triage: true` to frontmatter. Present the suggestion to the user and ask for confirmation.

### Frontmatter

Update the canonical note with this frontmatter:

```yaml
---
captured_at: <original timestamp, preserve if exists>
source: <original source, preserve if exists, default "claude-code">
para: <project|area|resource|archive|inbox>
status: <triaged|raw>
tags: [<suggested tags>]
triage_confidence: <0.0-1.0>
triage_notes: "<short explanation of routing decision>"
ai_generated: <preserve original value>
---
```

### Project-Specific Routing

If classified as a **project**, create the full project structure:

```
1_projects/active/<project-slug>/
├── index.md       (the triaged note content goes here)
├── tasks.md       (with basic frontmatter)
├── decisions.md   (with basic frontmatter)
├── notes/         (empty, with .gitkeep)
└── assets/        (empty, with .gitkeep)
```

The `<project-slug>` should be derived from the note title (lowercase, hyphenated). The `tasks.md` and `decisions.md` files should contain:
```yaml
---
para: project
project: <project-slug>
status: active
---
```

### Area/Resource Routing

Move the note into the appropriate subfolder:
- `2_areas/<AreaName>/<note-slug>.md`
- `3_resources/<ResourceName>/<note-slug>.md`

Create the subfolder if it doesn't exist.

### Raw Capture Preservation

After routing, ensure the original content is preserved. Add a section at the bottom of the canonical note:

```markdown
## Raw Capture

> (verbatim original content from inbox)
```

### Rules
- NEVER delete the original inbox file content — preserve it inline or as a sidecar
- Preserve the original `captured_at` timestamp
- Preserve the original `ai_generated` value
- If the note was clearly AI-synthesized (summaries, generated connections), set `ai_generated: true`

### Logging

After each item is processed, append an entry to `_system/processing-log.md`:
- timestamp, source path, destination path, confidence, any warnings

$ARGUMENTS
