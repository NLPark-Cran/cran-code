Replace specific strings within a specified file.

**Tips:**
- You must have read the file with ReadFile earlier in this session before editing it; otherwise the edit is rejected (read-before-write discipline).
- Only use this tool on text files.
- Multi-line strings are supported.
- Can specify a single edit or a list of edits in one call.
- You should prefer this tool over WriteFile tool and Shell `sed` command.
- DO NOT issue consecutive StrReplaceFile calls on the same file when the second edit's `old` text overlaps or follows the first edit's region: a previous edit can invalidate a later edit's `old` string, causing "old string not found". Read the file again before the next edit in that case. (Multiple edits in ONE call are applied in order and are safe when the regions don't overlap.)
