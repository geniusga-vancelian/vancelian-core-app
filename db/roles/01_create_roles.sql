-- Database roles for Vancelian Core App
-- This script creates separate read-only and read-write roles for enhanced security

-- Create read-write role (application default)
CREATE ROLE vancelian_readwrite WITH LOGIN PASSWORD NULL;

-- Create read-only role (for reporting, analytics, backups)
CREATE ROLE vancelian_readonly WITH LOGIN PASSWORD NULL;

-- Grant connection to database
GRANT CONNECT ON DATABASE vancelian_core TO vancelian_readwrite;
GRANT CONNECT ON DATABASE vancelian_core TO vancelian_readonly;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO vancelian_readwrite;
GRANT USAGE ON SCHEMA public TO vancelian_readonly;

-- Grant create on schema (for migrations - readwrite only)
ALTER SCHEMA public OWNER TO vancelian_readwrite;

-- Note: Table-specific grants will be set up after migrations
-- See 02_grant_permissions.sql

COMMENT ON ROLE vancelian_readwrite IS 'Application read-write role for Vancelian Core';
COMMENT ON ROLE vancelian_readonly IS 'Read-only role for reporting and analytics';


