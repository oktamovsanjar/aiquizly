-- UP
CREATE TABLE IF NOT EXISTS games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id),
    quiz_set_id UUID NOT NULL REFERENCES quiz_sets(id),
    user_id UUID NOT NULL REFERENCES users(id),
    mode VARCHAR(20) DEFAULT 'solo',
    status VARCHAR(20) DEFAULT 'active',
    total_questions INTEGER NOT NULL,
    current_question_index INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    wrong_answers INTEGER DEFAULT 0,
    skipped_answers INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    time_spent_seconds INTEGER DEFAULT 0,
    is_retry BOOLEAN DEFAULT false,
    parent_game_id UUID REFERENCES games(id),
    started_at TIMESTAMP DEFAULT now(),
    paused_at TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_games_user ON games(user_id);
CREATE INDEX IF NOT EXISTS idx_games_quiz ON games(quiz_id);
CREATE INDEX IF NOT EXISTS idx_games_set ON games(quiz_set_id);
CREATE INDEX IF NOT EXISTS idx_games_status ON games(status);
CREATE INDEX IF NOT EXISTS idx_games_user_status ON games(user_id, status);

CREATE TABLE IF NOT EXISTS answers (
    id UUID DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(id),
    user_id UUID NOT NULL REFERENCES users(id),
    selected_indices INTEGER[],
    is_correct BOOLEAN,
    time_spent_ms INTEGER,
    answered_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (id, answered_at)
) PARTITION BY RANGE (answered_at);

CREATE TABLE IF NOT EXISTS answers_2026_05 PARTITION OF answers
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE IF NOT EXISTS answers_2026_06 PARTITION OF answers
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE IF NOT EXISTS answers_2026_07 PARTITION OF answers
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE IF NOT EXISTS answers_2026_08 PARTITION OF answers
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE IF NOT EXISTS answers_2026_09 PARTITION OF answers
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE IF NOT EXISTS answers_2026_10 PARTITION OF answers
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE IF NOT EXISTS answers_2026_11 PARTITION OF answers
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE IF NOT EXISTS answers_2026_12 PARTITION OF answers
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

CREATE INDEX IF NOT EXISTS idx_answers_game ON answers(game_id);
CREATE INDEX IF NOT EXISTS idx_answers_user ON answers(user_id);

CREATE TABLE IF NOT EXISTS user_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    total_xp INTEGER DEFAULT 0,
    level VARCHAR(20) DEFAULT 'beginner',
    total_games INTEGER DEFAULT 0,
    total_correct INTEGER DEFAULT 0,
    total_wrong INTEGER DEFAULT 0,
    accuracy DECIMAL(5,2) DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_played_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_stats_xp ON user_stats(total_xp DESC);
CREATE INDEX IF NOT EXISTS idx_user_stats_streak ON user_stats(current_streak DESC);

CREATE TABLE IF NOT EXISTS xp_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    amount INTEGER NOT NULL,
    reason VARCHAR(50) NOT NULL,
    reference_id UUID,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_xp_logs_user ON xp_logs(user_id);

CREATE TABLE IF NOT EXISTS achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    xp_reward INTEGER DEFAULT 0,
    condition_type VARCHAR(50) NOT NULL,
    condition_value INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    achievement_id UUID NOT NULL REFERENCES achievements(id),
    unlocked_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_achievements_unique ON user_achievements(user_id, achievement_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);

CREATE TABLE IF NOT EXISTS leaderboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    tag_id UUID REFERENCES tags(id),
    period VARCHAR(20) NOT NULL,
    period_key VARCHAR(20) NOT NULL,
    total_games INTEGER DEFAULT 0,
    total_correct INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    accuracy DECIMAL(5,2) DEFAULT 0,
    rank INTEGER,
    updated_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_leaderboard_unique
    ON leaderboards(user_id, COALESCE(tag_id, '00000000-0000-0000-0000-000000000000'::UUID), period, period_key);
CREATE INDEX IF NOT EXISTS idx_leaderboard_rank
    ON leaderboards(period, period_key, total_score DESC);

-- Boshlang'ich yutuqlar
INSERT INTO achievements (slug, name, description, icon, xp_reward, condition_type, condition_value)
VALUES
    ('first_quiz', 'Birinchi quiz', 'Birinchi quiz yechish', '🎯', 0, 'games_count', 1),
    ('7_day_streak', '7 kunlik streak', 'Ketma-ket 7 kun', '🔥', 50, 'streak_days', 7),
    ('perfect_score', 'Mukammal', 'Biror setda 100% to''g''ri', '💯', 0, 'accuracy', 100),
    ('first_upload', 'Muallif', 'Birinchi quiz yaratish', '📤', 20, 'quiz_created', 1),
    ('top_10', 'Top 10', 'Haftalik reytingga kirish', '🏆', 100, 'weekly_top', 10),
    ('1000_questions', '1000 savol', 'Jami 1000 savolga javob berish', '📚', 0, 'total_answers', 1000),
    ('academic_level', 'Akademik', 'Eng yuqori darajaga yetish', '👑', 0, 'level', 6)
ON CONFLICT DO NOTHING;

-- DOWN
-- DROP TABLE IF EXISTS leaderboards, user_achievements, achievements, xp_logs, user_stats, answers, games;
