-- Incidentra PostgreSQL initialization
-- Run as postgres superuser: psql -U postgres -f scripts/init_postgres.sql

CREATE USER incidentra WITH PASSWORD 'incidentra123';
CREATE DATABASE incidentra_db OWNER incidentra;
GRANT ALL PRIVILEGES ON DATABASE incidentra_db TO incidentra;
ALTER DATABASE incidentra_db SET timezone TO 'UTC';
\c incidentra_db
GRANT ALL ON SCHEMA public TO incidentra;
