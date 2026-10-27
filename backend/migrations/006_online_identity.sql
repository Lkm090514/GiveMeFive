-- Additive only: preserve all existing owners, imports, sessions and answer records.
CREATE TABLE IF NOT EXISTS v43_users(user_id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','student')),created_at INTEGER NOT NULL,disabled INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS v43_logins(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES v43_users(user_id),expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS v43_invites(invite_hash TEXT PRIMARY KEY,email TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','student')),expires_at INTEGER NOT NULL,used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS v43_login_limits(bucket TEXT PRIMARY KEY,attempts INTEGER NOT NULL,reset_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS v43_paper_reviews(set_id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL);
