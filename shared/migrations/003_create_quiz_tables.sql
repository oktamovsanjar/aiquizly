-- UP
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

-- DOWN
-- DROP TABLE IF EXISTS telegram_groups, referrals, quiz_group_subscribers, quiz_groups, tags;
