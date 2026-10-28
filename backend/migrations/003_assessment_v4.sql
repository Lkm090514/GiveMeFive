-- Extends the existing V3 database. Public Question/Version/Answer remain V3 tables.
CREATE TABLE IF NOT EXISTS v4_meta(version_id TEXT PRIMARY KEY REFERENCES question_versions, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS v4_sets(set_id TEXT PRIMARY KEY, document_id TEXT, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS v4_sessions(session_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, mode TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS v4_session_owner ON v4_sessions(owner_id,status);
CREATE UNIQUE INDEX IF NOT EXISTS v4_one_exam ON v4_sessions(owner_id) WHERE mode='exam' AND status='active';
CREATE TABLE IF NOT EXISTS v4_answers(record_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, session_id TEXT NOT NULL REFERENCES v4_sessions, question_id TEXT NOT NULL REFERENCES questions, version_id TEXT NOT NULL REFERENCES question_versions, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS v4_wrong(owner_id TEXT NOT NULL, question_id TEXT NOT NULL REFERENCES questions, payload TEXT NOT NULL, PRIMARY KEY(owner_id,question_id));
CREATE TABLE IF NOT EXISTS v4_imports(owner_id TEXT NOT NULL, request_key TEXT NOT NULL, file_sha TEXT NOT NULL, batch_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(owner_id,request_key));
CREATE TABLE IF NOT EXISTS v4_grades(grade_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES v4_sessions, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS v4_bookmarks(owner_id TEXT NOT NULL, question_id TEXT NOT NULL, PRIMARY KEY(owner_id,question_id));
CREATE TABLE IF NOT EXISTS v4_type_reviews(classification_id TEXT PRIMARY KEY REFERENCES classifications(classification_id), version_id TEXT NOT NULL REFERENCES question_versions, payload TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS v4_classification_version ON classifications(version_id,seq DESC);
CREATE TRIGGER IF NOT EXISTS v4_type_reviews_immutable BEFORE UPDATE ON v4_type_reviews BEGIN SELECT RAISE(ABORT,'type reviews immutable'); END;
CREATE TRIGGER IF NOT EXISTS v4_type_reviews_no_delete BEFORE DELETE ON v4_type_reviews BEGIN SELECT RAISE(ABORT,'type reviews immutable'); END;
CREATE TRIGGER IF NOT EXISTS v4_answers_immutable BEFORE UPDATE ON v4_answers BEGIN SELECT RAISE(ABORT,'answer records immutable'); END;
CREATE TRIGGER IF NOT EXISTS v4_answers_no_delete BEFORE DELETE ON v4_answers BEGIN SELECT RAISE(ABORT,'answer records immutable'); END;
CREATE TRIGGER IF NOT EXISTS v4_grades_immutable BEFORE UPDATE ON v4_grades BEGIN SELECT RAISE(ABORT,'grade revisions immutable'); END;
