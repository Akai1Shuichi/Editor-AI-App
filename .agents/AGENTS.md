# Fast, token-efficient workflow

These instructions apply to all work in this repository unless the user says otherwise.

- Prioritize speed and low token usage for routine, reversible changes.
- Never spawn subagents or delegate work unless the user explicitly asks for agents in the current request.
- The user will test application behavior. Do not run automated tests, builds, linters, app launches, screenshots, UI smoke tests, or manual feature checks unless the user explicitly asks for testing or verification.
- For bounded changes, inspect only the relevant files and line ranges, then implement directly. Do not create plans, specs, design documents, or approval checkpoints unless a missing decision would materially change the result.
- Avoid broad repository scans, full-file dumps, repeated diffs, repeated verification, and unrelated investigation.
- Do not browse the web or load extra documentation unless the user asks or a higher-priority instruction requires it.
- Do not use optional review workflows or optional skills that add process without being necessary to complete the requested edit.
- Preserve existing user changes and keep edits strictly within the requested scope.
- Make reasonable assumptions from the current code and conversation. Mention important assumptions briefly in the final response instead of stopping for minor clarification.
- Keep progress updates and the final response concise. State which files changed and leave functional testing to the user.

Higher-priority system, developer, safety, and explicit user instructions still take precedence over this file.
