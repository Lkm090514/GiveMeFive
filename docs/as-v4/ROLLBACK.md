# Rollback

1. Stop the Python server. Copy the whole runtime/v4 directory, including SQLite and assets, to a dated backup.
2. Preserve/export the browser's existing PL/MF backup before testing a different origin or browser.
3. The Fusion baseline is ccadc3ce4e34fbe7081fae0a08373f5f60c98a19. On the V4 branch, commit any intended local work before switching the checkout to that baseline. Do not reset someone else's uncommitted changes.
4. V4 database migrations are additive. Keep V4 session/response/grade tables when testing older code; do not delete or overwrite runtime/v4 with an empty package directory.
5. This turn does not overwrite the existing static production deployment. Local rollback has no hosting side effects.
