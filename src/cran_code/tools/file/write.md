Write content to a file.

**Tips:**
- To modify an EXISTING file, you must have read it with ReadFile earlier in this session; otherwise the write is rejected (read-before-write discipline). Creating new files is always allowed.
- When `mode` is not specified, it defaults to `overwrite`. Always write with caution.
- When the content to write is too long (e.g. > 100 lines), use this tool multiple times instead of a single call. Use `overwrite` mode at the first time, then use `append` mode after the first write.
