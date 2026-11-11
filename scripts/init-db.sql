-- ============================================================================
-- HMS Platform - Database Initialization Script
-- Creates required extensions for the HMS database
-- ============================================================================

-- Enable pgcrypto extension for encryption functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Grant usage to hms_user
GRANT ALL PRIVILEGES ON DATABASE hms_db TO hms_user;
