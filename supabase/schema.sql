-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create knowledge_documents table with vector embeddings
CREATE TABLE IF NOT EXISTS knowledge_documents (
  id BIGSERIAL PRIMARY KEY,
  document_id TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(1536),
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_category (category),
  INDEX idx_document_id (document_id)
);

-- Create index for vector similarity search (cosine distance)
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding_cosine
ON knowledge_documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create users table for Telegram bot user persistence
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  telegram_user_id BIGINT UNIQUE NOT NULL,
  first_name TEXT,
  username TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  conversation_count INT DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  metadata JSONB DEFAULT '{}'::jsonb,
  INDEX idx_telegram_user_id (telegram_user_id)
);

-- Create conversations table for chat history
CREATE TABLE IF NOT EXISTS conversations (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  message_text TEXT NOT NULL,
  response_text TEXT,
  context_documents JSONB,
  tokens_used INT DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_id (user_id),
  INDEX idx_created_at (created_at)
);

-- Create index for recent conversations lookup
CREATE INDEX IF NOT EXISTS idx_user_id_created_at
ON conversations (user_id, created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Allow public read access to knowledge_documents
CREATE POLICY "knowledge_documents_select"
ON knowledge_documents
FOR SELECT
USING (true);

-- RLS Policies: Allow service role to insert/update knowledge_documents
CREATE POLICY "knowledge_documents_insert_service"
ON knowledge_documents
FOR INSERT
WITH CHECK (true);

CREATE POLICY "knowledge_documents_update_service"
ON knowledge_documents
FOR UPDATE
USING (true);

-- RLS Policies for users table (each user can only see their own data)
CREATE POLICY "users_select_own"
ON users
FOR SELECT
USING (auth.uid()::bigint = telegram_user_id OR auth.role() = 'service_role');

CREATE POLICY "users_insert"
ON users
FOR INSERT
WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "users_update_own"
ON users
FOR UPDATE
USING (auth.uid()::bigint = telegram_user_id OR auth.role() = 'service_role');

-- RLS Policies for conversations table
CREATE POLICY "conversations_select_own"
ON conversations
FOR SELECT
USING (
  auth.role() = 'service_role' OR
  user_id IN (SELECT id FROM users WHERE telegram_user_id = auth.uid()::bigint)
);

CREATE POLICY "conversations_insert"
ON conversations
FOR INSERT
WITH CHECK (auth.role() = 'service_role');

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_knowledge_documents_updated_at BEFORE UPDATE ON knowledge_documents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for convenient similarity search
CREATE OR REPLACE VIEW knowledge_search AS
SELECT
  id,
  document_id,
  title,
  category,
  content,
  embedding,
  created_at
FROM knowledge_documents
ORDER BY created_at DESC;
