-- UP
CREATE TABLE IF NOT EXISTS quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    quiz_group_id UUID REFERENCES quiz_groups(id),
    title VARCHAR(300) NOT NULL,
    description TEXT,
    visibility VARCHAR(20) DEFAULT 'private',
    source_type VARCHAR(20),
    total_questions INTEGER DEFAULT 0,
    time_per_question INTEGER DEFAULT 30,
    play_count INTEGER DEFAULT 0,
    avg_rating DECIMAL(3,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quizzes_owner ON quizzes(owner_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_group ON quizzes(quiz_group_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_visibility ON quizzes(visibility);
CREATE INDEX IF NOT EXISTS idx_quizzes_play_count ON quizzes(play_count DESC);
CREATE INDEX IF NOT EXISTS idx_quizzes_expires ON quizzes(expires_at);

CREATE TABLE IF NOT EXISTS quiz_tags (
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (quiz_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_tags_tag ON quiz_tags(tag_id);

CREATE TABLE IF NOT EXISTS quiz_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    set_number INTEGER NOT NULL,
    title VARCHAR(100),
    question_count INTEGER NOT NULL,
    start_index INTEGER NOT NULL,
    end_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_quiz_sets_unique ON quiz_sets(quiz_id, set_number);
CREATE INDEX IF NOT EXISTS idx_quiz_sets_quiz ON quiz_sets(quiz_id);

CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) DEFAULT 'single',
    options JSONB NOT NULL,
    correct_indices INTEGER[] NOT NULL,
    explanation TEXT,
    media_url VARCHAR(500),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_questions_quiz ON questions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_questions_sort ON questions(quiz_id, sort_order);

CREATE TABLE IF NOT EXISTS import_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    quiz_id UUID REFERENCES quizzes(id),
    file_name VARCHAR(500) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_size INTEGER,
    file_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_detected INTEGER DEFAULT 0,
    total_imported INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT now(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_import_user ON import_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_import_hash ON import_logs(file_hash);
CREATE INDEX IF NOT EXISTS idx_import_status ON import_logs(status);

-- DOWN
-- DROP TABLE IF EXISTS import_logs, questions, quiz_sets, quiz_tags, quizzes;
