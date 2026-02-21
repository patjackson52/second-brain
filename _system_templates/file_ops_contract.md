# File Operations Contract (Secondbrain PARA System)

This document defines safe, deterministic rules for any automation/agent that reads/writes the vault.

## 1. Core Principles
1) Filesystem is the source of truth (Markdown + assets).
2) Preserve originals: automation must be non-destructive.
3) Idempotence: re-running triage should not create duplicates or thrash files.
4) Auditability: every action must be logged.

## 2. Non-Destructive Policy
- NEVER permanently delete user content.
- Allowed operations:
  - Create new files
  - Move files
  - Copy files
  - Append or minimally edit files
- Disallowed:
  - Deleting original inbox items
  - Rewriting a note without preserving raw capture
  - Removing user-authored sections without explicit instruction

## 3. Raw Capture Preservation
Every inbox item must remain accessible after triage via one of:

### Option A (inline preservation, preferred)
Canonical note contains:

## Raw Capture
> (verbatim original content, or a link to the original file)

### Option B (sidecar preservation)
Keep original file + add a sidecar:
- `original.ext` + `original.md` OR `original.meta.json`
And the canonical note links to it.

## 4. Canonical Note Creation Rules
When converting an inbox item into a note:
- Create a canonical note path under PARA (project/area/resource/archive).
- Add frontmatter fields:
  - captured_at, source, para, status, triage_confidence
- Add a short summary section.
- Preserve raw capture (Section 3).

### Idempotence
- If a canonical note already exists for that inbox item:
  - Update in place (append new info), do not create another note.
- Use stable identifiers:
  - Either a generated `id:` in frontmatter, OR
  - A stable filename derived from timestamp + slug.

## 5. Moves vs Copies
- Default: MOVE inbox items to destination once successfully triaged.
- Exception: If confidence below configured threshold:
  - EITHER keep in inbox and mark `needs_triage: true`,
  - OR copy to destination and leave the inbox item (depending on routes.yaml policy).

## 6. Asset Handling
- Assets (images/audio/pdf) should be moved into `_assets/<type>/YYYY/MM/` (or configured scheme).
- The canonical note must link to the asset with a relative path.
- Do not duplicate large binaries unless necessary.
- If an inbox bundle contains multiple assets:
  - Create one canonical note that links all assets and includes a summary.

## 7. Folder Safety
- Agents must only write within:
  - `0_inbox/`, `1_projects/`, `2_areas/`, `3_resources/`, `4_archive/`, `5_people/`, `_assets/`, `_system/`
- Agents must not write outside the vault root.

## 8. Logging (Required)
Append one entry per processed item to `_system/processing-log.md`:

- timestamp
- agent name/version
- source path
- destination path
- operations performed (move/copy/create/update)
- triage_confidence
- any warnings (needs_review, missing metadata, etc.)

## 9. Conflict Handling (Sync + Multi-device)
- Assume files may arrive out of order.
- If a filename conflict exists:
  - Prefer renaming the new file with a suffix: `__conflict-<shortid>`
  - Log the conflict.
- Never discard conflicting versions.

## 10. Safety Checks Before Finalizing
Before considering a triage "successful", ensure:
- canonical note exists and is readable markdown
- raw capture is preserved and referenced
- any assets are present and linked
- log entry written
If any check fails:
- do not move/delete the original inbox item
- mark `needs_triage: true` and log an error
