-- PostgreSQL extension lar
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'uz',
    is_bot_blocked BOOLEAN DEFAULT false,
    referred_by UUID REFERENCES users(id),
    last_active_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active_at);
CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by);


CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    price_monthly INTEGER DEFAULT 0,
    price_yearly INTEGER DEFAULT 0,
    max_uploads_per_month INTEGER,
    max_questions_per_file INTEGER,
    can_share_group BOOLEAN DEFAULT false,
    can_create_quiz_group BOOLEAN DEFAULT false,
    can_publish BOOLEAN DEFAULT false,
    quiz_retention_days INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    plan_id UUID NOT NULL REFERENCES plans(id),
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires ON subscriptions(expires_at);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    subscription_id UUID REFERENCES subscriptions(id),
    provider VARCHAR(20) NOT NULL,
    provider_payment_id VARCHAR(255),
    amount INTEGER NOT NULL,
    currency VARCHAR(10) DEFAULT 'UZS',
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    month VARCHAR(7) NOT NULL,
    count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_user_action_month
    ON usage_logs(user_id, action, month);

-- Boshlang'ich tarif rejalarini qo'shish
INSERT INTO plans (name, price_monthly, price_yearly, max_uploads_per_month, max_questions_per_file, can_share_group, can_create_quiz_group, can_publish, quiz_retention_days, is_active)
VALUES
    ('free', 0, 0, 3, 50, false, false, false, 7, true),
    ('premium', 29000, 249000, NULL, NULL, true, true, true, NULL, true),
    ('business', NULL, NULL, NULL, NULL, true, true, true, NULL, true)
ON CONFLICT DO NOTHING;


CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tags_slug ON tags(slug);
CREATE INDEX IF NOT EXISTS idx_tags_usage ON tags(usage_count DESC);

CREATE TABLE IF NOT EXISTS quiz_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(100) UNIQUE NOT NULL,
    subscriber_count INTEGER DEFAULT 0,
    quiz_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_quiz_groups_owner ON quiz_groups(owner_id);
CREATE INDEX IF NOT EXISTS idx_quiz_groups_slug ON quiz_groups(slug);
CREATE INDEX IF NOT EXISTS idx_quiz_groups_subscribers ON quiz_groups(subscriber_count DESC);

CREATE TABLE IF NOT EXISTS quiz_group_subscribers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_group_id UUID NOT NULL REFERENCES quiz_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    notify BOOLEAN DEFAULT true,
    subscribed_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_qgs_unique ON quiz_group_subscribers(quiz_group_id, user_id);
CREATE INDEX IF NOT EXISTS idx_qgs_user ON quiz_group_subscribers(user_id);

CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES users(id),
    referred_id UUID NOT NULL REFERENCES users(id),
    bonus_given BOOLEAN DEFAULT false,
    bonus_days INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_referrals_unique ON referrals(referrer_id, referred_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);

CREATE TABLE IF NOT EXISTS telegram_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id BIGINT UNIQUE NOT NULL,
    title VARCHAR(255),
    added_by UUID REFERENCES users(id),
    voting_enabled BOOLEAN DEFAULT true,
    min_voters INTEGER DEFAULT 3,
    voting_timeout INTEGER DEFAULT 60,
    who_can_start VARCHAR(20) DEFAULT 'admin',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_telegram_groups_chat ON telegram_groups(chat_id);


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
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(id),
    user_id UUID NOT NULL REFERENCES users(id),
    selected_indices INTEGER[],
    is_correct BOOLEAN,
    time_spent_ms INTEGER,
    answered_at TIMESTAMP DEFAULT now()
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


CREATE TABLE IF NOT EXISTS notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    text_uz TEXT NOT NULL,
    text_ru TEXT,
    text_en TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    template_id UUID REFERENCES notification_templates(id),
    custom_text TEXT,
    reference_type VARCHAR(50),
    reference_id UUID,
    status VARCHAR(20) DEFAULT 'pending',
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);

CREATE TABLE IF NOT EXISTS admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    role VARCHAR(20) DEFAULT 'moderator',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT now()
);

-- Notification shablonlari
INSERT INTO notification_templates (slug, text_uz, text_ru, text_en)
VALUES
    ('quiz_ready', '✅ "{title}" tayyor!\n{total_questions} savol → {total_sets} set', NULL, NULL),
    ('daily_reminder', '🔥 {streak} kunlik streak!\nBugun ham davom ettiring.', NULL, NULL),
    ('new_quiz_in_group', '📌 {group_name} — yangi quiz!\n📋 "{quiz_title}"\n{total_questions} savol | {total_sets} set', NULL, NULL),
    ('achievement_unlocked', '🏅 Yangi yutuq: "{achievement_name}"!\n+{xp} XP qo''shildi', NULL, NULL),
    ('referral_joined', '👥 Do''stingiz @{username} ro''yxatdan o''tdi!\n+50 XP va +3 kun premium qo''shildi', NULL, NULL),
    ('streak_broken', '😔 Streak uzildi ({streak} kun edi)\nQaytadan boshlang!', NULL, NULL)
ON CONFLICT DO NOTHING;

-- Boshlang'ich sozlamalar
INSERT INTO settings (key, value, description)
VALUES
    ('maintenance_mode', 'false', 'Texnik ishlar rejimi'),
    ('max_file_size_mb', '10', 'Maksimal fayl hajmi (MB)'),
    ('default_set_size', '20', 'Set uchun standart savol soni')
ON CONFLICT DO NOTHING;


