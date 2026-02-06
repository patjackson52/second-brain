Classify and route notes from the inbox to the appropriate bucket.

## Instructions

### Input
- If `$ARGUMENTS` is a specific file path: classify only that file
- If `$ARGUMENTS` is "all" or empty: process all files in `inbox/` (excluding .gitkeep)

### Classification

For each file, read its content and determine:

| Field           | Values                                      |
|-----------------|---------------------------------------------|
| Target bucket   | One of: `ideas`, `projects`, `people`, `admin` |
| `type` value    | `idea`, `project`, `person`, or `admin`     |
| Suggested tags  | List of relevant tags                       |
| Confidence      | Float 0.0–1.0                               |

### Routing

- **High confidence (> 0.6):** Move file to target bucket, update frontmatter:
  ```yaml
  ---
  type: <classified type>
  captured_at: <original timestamp>
  source: claude-code
  tags: [<suggested tags>]
  confidence: <0.0-1.0>
  ai_generated: false
  ---
  ```

- **Low confidence (<= 0.6):** Present the suggestion to the user and ask for confirmation or override. Do NOT move the file until the user confirms.

- **Project-specific routing:** If a note is classified as a `project`, create a subdirectory structure instead of a single file:
  ```
  projects/<project-slug>/
  ├── overview.md    (the triaged file content goes here)
  ├── tasks.md       (empty with basic frontmatter)
  └── decisions.md   (empty with basic frontmatter)
  ```
  The `<project-slug>` should be derived from the note title (lowercase, hyphenated). The `tasks.md` and `decisions.md` files should contain only basic frontmatter:
  ```yaml
  ---
  type: project
  project: <project-slug>
  ---
  ```

### Rules
- Preserve the original note body unchanged
- Preserve the original `captured_at` timestamp
- Preserve the original `ai_generated` value
- If the note was clearly AI-synthesized (summaries, generated connections), set `ai_generated: true`

$ARGUMENTS
