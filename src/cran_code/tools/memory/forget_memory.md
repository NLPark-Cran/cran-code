Forget (archive) one of the current user's cross-session memories by id.

## When to Use
- The user explicitly asks to forget something.
- A remembered fact is wrong or stale enough to be misleading.

Archiving is reversible in the database but the memory immediately stops appearing in session-start briefs and search results. Get ids from `SearchMemory` output.
