-- Removing a failed task from the list preserves source PDFs and audit records.
CREATE TABLE IF NOT EXISTS v4_import_archives (
  owner_id TEXT NOT NULL,
  batch_id TEXT NOT NULL,
  archived_at TEXT NOT NULL,
  PRIMARY KEY (owner_id, batch_id)
);
