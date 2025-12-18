-- Grant table permissions to roles
-- This script should be run AFTER migrations have created all tables

-- Grant ALL privileges on ALL tables to readwrite role
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO vancelian_readwrite;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO vancelian_readwrite;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO vancelian_readwrite;

-- Grant SELECT only on ALL tables to readonly role (least privilege)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO vancelian_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO vancelian_readonly;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL PRIVILEGES ON TABLES TO vancelian_readwrite;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO vancelian_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL PRIVILEGES ON SEQUENCES TO vancelian_readwrite;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON SEQUENCES TO vancelian_readonly;

COMMENT ON ROLE vancelian_readwrite IS 'Has full read-write access to all tables';
COMMENT ON ROLE vancelian_readonly IS 'Has read-only access to all tables';


