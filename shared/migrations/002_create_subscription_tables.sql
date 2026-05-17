-- UP
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

-- DOWN
-- DROP TABLE IF EXISTS usage_logs, payments, subscriptions, plans;
