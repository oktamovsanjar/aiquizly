-- UP
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

-- DOWN
-- DROP TABLE IF EXISTS settings, admins, notifications, notification_templates;
