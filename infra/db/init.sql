-- HydroQ-QC-Assistant Database Initialization
-- Run with: psql -U postgres -f init.sql

-- Create database if not exists (run this separately if needed)
-- CREATE DATABASE hydroq_qc;

-- Connect to database
\c hydroq_qc;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";  -- Optional: for spatial operations

-- Create enum types
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'hydrographer', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE run_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE confidence_level AS ENUM ('low', 'medium', 'high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE review_decision AS ENUM ('pending', 'accepted', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Note: Actual table creation is handled by Alembic migrations
-- This script only initializes extensions and custom types

-- Grant privileges (adjust as needed)
-- GRANT ALL PRIVILEGES ON DATABASE hydroq_qc TO hydroq_user;

COMMENT ON DATABASE hydroq_qc IS 'HydroQ-QC-Assistant: Multibeam Bathymetry QC Decision Support System';
