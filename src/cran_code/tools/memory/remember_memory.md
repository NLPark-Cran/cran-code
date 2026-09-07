Save a durable fact about the user to cross-session memory. Remembered items are injected as a brief at the start of the user's future sessions and are searchable via `SearchMemory`.

## When to Use
Save only things that will still matter in a FUTURE session:
- stable user preferences (editor, language, style, workflow habits),
- decisions with lasting rationale ("we chose sqlite over postgres because …"),
- environment facts / gotchas worth not rediscovering ("deploy port 5496 is occupied by prod").
Do NOT save ephemeral task state (that belongs in the conversation/todo list) or anything the user asked to keep private.

## Rules
- NEVER store secrets: tokens, API keys, passwords, private URLs with credentials. Content matching credential patterns is rejected.
- Write self-contained one-or-two-sentence entries; future sessions see them without this conversation's context.
- Duplicates are merged automatically: re-remembering a similar fact updates it and bumps its salience instead of creating a copy.
- Use `salience` sparingly: default 1.0 is right for most items; reserve higher values for things that must surface first.
