-----------------------------
-- Database Initialization Script for IntelliMind
-- Version: 1.2
-- Purpose: Core system setup with demo data and bcrypt password hashing
-----------------------------

-----------------------------
-- 1. Enable Required Extensions
-----------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- Enable fuzzy text search
CREATE EXTENSION IF NOT EXISTS btree_gin; -- Support for JSONB and array indexing


-- Create custom ENUM types
CREATE TYPE file_type AS ENUM ('pdf', 'image');
CREATE TYPE ocr_engine AS ENUM ('paddleocr', 'tesseract', 'easyocr', 'pdfplumber');
CREATE TYPE processing_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE user_role AS ENUM (
    'anonymous',
    'user',
    'admin',
    'moderator'
);


-- User Accounts
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    mobile VARCHAR(20) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,  -- BCrypt encrypted
    role user_role DEFAULT 'user',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_mobile ON users(mobile);
CREATE INDEX idx_users_role ON users(role);

-- Create documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    file_type file_type NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    upload_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    status processing_status DEFAULT 'pending' NOT NULL,
    searchable_content TEXT,
    recommendation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(150) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(150) NOT NULL
);

-- Create indexes for documents
CREATE INDEX idx_document_filename ON documents (filename);
CREATE INDEX idx_document_upload_time ON documents (upload_timestamp);
CREATE INDEX idx_document_status ON documents (status);

-- Create ocr_results table
CREATE TABLE ocr_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL,
    engine ocr_engine NOT NULL,
    extracted_text TEXT NOT NULL,
    confidence_score REAL,
    processing_time_ms INTEGER NOT NULL,
    page_metrics JSONB,
    estimated_cost REAL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(150) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(150) NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Create indexes for ocr_results
CREATE INDEX idx_ocr_document_engine ON ocr_results (document_id, engine);
CREATE INDEX idx_ocr_engine ON ocr_results (engine);
CREATE INDEX idx_ocr_processed_at ON ocr_results (processed_at);
CREATE INDEX idx_ocr_confidence ON ocr_results (confidence_score);
CREATE INDEX idx_ocr_processing_time ON ocr_results (processing_time_ms);

-- User Accounts with bcrypt hashed passwords
-- WARNING: These are for development purposes only
INSERT INTO users (id, username, email, hashed_password, role) VALUES
('a0eebc99-110b-4ef8-bb6d-6bb9bd380a01', 'admin', 'admin@ocr.ai', '$2b$12$X3JFkTQHvhhAUKzoIy80lO.opgjAwdguBbzbwkJPV4ziSAUcHMUW2', 'admin'), -- Password: admin
('b0eebc99-110b-4ef8-bb6d-6bb9bd380a02', 'user', 'user@ocr.ai', '$2b$12$pOO/vHVHf1cUjEQ6RakCsebMma9Qyfxn5jAlGzHLNy5MtQbNDj5eW', 'user'), -- Password: 123456
('c0eebc99-110b-4ef8-bb6d-6bb9bd380a03', 'user2', 'user2@ocr.ai', '$2b$12$pOO/vHVHf1cUjEQ6RakCsebMma9Qyfxn5jAlGzHLNy5MtQbNDj5eW', 'user'); -- Password: 123456