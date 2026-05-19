-- SME-Guard PostgreSQL initialization
-- Run as postgres superuser: psql -U postgres -f scripts/init_postgres.sql

CREATE USER smeguard WITH PASSWORD 'smeguard123';
CREATE DATABASE smeguard_db OWNER smeguard;
GRANT ALL PRIVILEGES ON DATABASE smeguard_db TO smeguard;
ALTER DATABASE smeguard_db SET timezone TO 'UTC';
\c smeguard_db
GRANT ALL ON SCHEMA public TO smeguard;
