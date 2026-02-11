Create a new note in the inbox from the user's input.

## Instructions

1. Get the current local time by running: `date +%Y-%m-%dT%H:%M:%S%z`
   - Use this timestamp for both the filename and `captured_at` field

2. Generate a filename using the timestamp and a short slug derived from the content:
   - Format: `YYYY-MM-DD-HHMM-<slug>.md` (e.g., `2026-01-22-1534-quick-thought.md`)
   - Slug: lowercase, hyphens, max 5 words from the content

3. Create the file in `0_inbox/` with this structure:

```
---
type: unknown
captured_at: <current ISO-8601 timestamp>
source: claude-code
ai_generated: false
---

<user's content here>
```

4. After creating the file, automatically run `/triage` on the newly created file.

## User's note content

$ARGUMENTS
