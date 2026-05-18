# Quiz Bot — Database Schema

## Umumiy Qoidalar

```
- PostgreSQL 16+
- UUID primary key (integer emas — distributed system uchun)
- Barcha jadvallar created_at, updated_at bilan
- Soft delete: deleted_at (haqiqiy o'chirish yo'q)
- Index: tez-tez so'raladigan ustunlarga
- Partitioning: answers jadvali (million qator uchun)
```

---

## 1. Users (bot xizmati)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'uz',
    is_bot_blocked BOOLEAN DEFAULT false,
    referred_by UUID REFERENCES users(id),    -- kim taklif qilgan
    last_active_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_last_active ON users(last_active_at);
CREATE INDEX idx_users_referred_by ON users(referred_by);
```

---

## 2. Subscriptions va To'lovlar (subscription xizmati)

```sql
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,              -- free, premium, business
    price_monthly INTEGER DEFAULT 0,         -- tiyin/cent
    price_yearly INTEGER DEFAULT 0,
    max_uploads_per_month INTEGER,           -- null = cheksiz
    max_questions_per_file INTEGER,          -- null = cheksiz
    can_share_group BOOLEAN DEFAULT false,
    can_create_quiz_group BOOLEAN DEFAULT false,
    can_publish BOOLEAN DEFAULT false,
    quiz_retention_days INTEGER,              -- null = cheksiz
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    plan_id UUID NOT NULL REFERENCES plans(id),
    status VARCHAR(20) NOT NULL,             -- active, expired, cancelled
    started_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_expires ON subscriptions(expires_at);

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    subscription_id UUID REFERENCES subscriptions(id),
    provider VARCHAR(20) NOT NULL,           -- telegram_stars, payme, click, stripe
    provider_payment_id VARCHAR(255),
    amount INTEGER NOT NULL,                 -- tiyin/cent
    currency VARCHAR(10) DEFAULT 'UZS',
    status VARCHAR(20) NOT NULL,             -- pending, completed, failed, refunded
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);

CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(50) NOT NULL,             -- file_upload, quiz_create
    month VARCHAR(7) NOT NULL,               -- '2026-05' (oylik limit uchun)
    count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX idx_usage_user_action_month
    ON usage_logs(user_id, action, month);
```

---

## 3. Teglar (ai-engine xizmati)

```sql
-- Kategoriya o'rniga teglar ishlatiladi (erkin, ierarxiyasiz)
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,              -- "DTM", "Ingliz tili", "IELTS"
    slug VARCHAR(100) UNIQUE NOT NULL,       -- "dtm", "ingliz_tili", "ielts"
    usage_count INTEGER DEFAULT 0,           -- nechta quiz ishlatgan (trend uchun)
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_tags_slug ON tags(slug);
CREATE INDEX idx_tags_usage ON tags(usage_count DESC);
```

---

## 4. Quiz Guruhlar (bot xizmati)

```sql
-- Quiz Guruh = foydalanuvchining quiz kanali (Telegram guruh EMAS)
CREATE TABLE quiz_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(100) UNIQUE NOT NULL,       -- link uchun: t.me/bot?start=g_{slug}
    subscriber_count INTEGER DEFAULT 0,
    quiz_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_quiz_groups_owner ON quiz_groups(owner_id);
CREATE INDEX idx_quiz_groups_slug ON quiz_groups(slug);
CREATE INDEX idx_quiz_groups_subscribers ON quiz_groups(subscriber_count DESC);

-- Obunalar (kim qaysi quiz guruhga obuna)
CREATE TABLE quiz_group_subscribers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_group_id UUID NOT NULL REFERENCES quiz_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    notify BOOLEAN DEFAULT true,             -- xabar olish on/off
    subscribed_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX idx_qgs_unique ON quiz_group_subscribers(quiz_group_id, user_id);
CREATE INDEX idx_qgs_user ON quiz_group_subscribers(user_id);
```

---

## 5. Quizzes — To'plamlar (ai-engine xizmati)

```sql
CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    quiz_group_id UUID REFERENCES quiz_groups(id),  -- qaysi guruhga biriktirilgan
    title VARCHAR(300) NOT NULL,
    description TEXT,
    visibility VARCHAR(20) DEFAULT 'private',       -- private, public
    source_type VARCHAR(20),                         -- upload, manual, ai_generated
    total_questions INTEGER DEFAULT 0,
    time_per_question INTEGER DEFAULT 30,            -- soniya (15, 30, 45, 60)
    play_count INTEGER DEFAULT 0,                    -- necha marta o'ynalgan
    avg_rating DECIMAL(3,2) DEFAULT 0,              -- o'rtacha baho (1-5)
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,                            -- free user uchun 7 kun
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_quizzes_owner ON quizzes(owner_id);
CREATE INDEX idx_quizzes_group ON quizzes(quiz_group_id);
CREATE INDEX idx_quizzes_visibility ON quizzes(visibility);
CREATE INDEX idx_quizzes_play_count ON quizzes(play_count DESC);
CREATE INDEX idx_quizzes_expires ON quizzes(expires_at);

-- Quiz va Teg bog'lanishi (many-to-many)
CREATE TABLE quiz_tags (
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (quiz_id, tag_id)
);

CREATE INDEX idx_quiz_tags_tag ON quiz_tags(tag_id);
```

---

## 6. Quiz Sets — To'plam Bo'linishi (ai-engine xizmati)

```sql
-- 500 savollik quiz → 25 set (20 tadan)
CREATE TABLE quiz_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    set_number INTEGER NOT NULL,              -- 1, 2, 3, ...
    title VARCHAR(100),                       -- "Set 1" (default)
    question_count INTEGER NOT NULL,          -- 20 (default)
    start_index INTEGER NOT NULL,             -- 0, 20, 40, ...
    end_index INTEGER NOT NULL,              -- 19, 39, 59, ...
    created_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX idx_quiz_sets_unique ON quiz_sets(quiz_id, set_number);
CREATE INDEX idx_quiz_sets_quiz ON quiz_sets(quiz_id);
```

---

## 7. Questions — Savollar (ai-engine xizmati)

```sql
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) DEFAULT 'single',  -- single, multiple
    options JSONB NOT NULL,                       -- ["variant1", "variant2", ...]
    correct_indices INTEGER[] NOT NULL,           -- {1} yoki {0,2}
    explanation TEXT,
    media_url VARCHAR(500),                      -- rasm/video (ixtiyoriy)
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_questions_quiz ON questions(quiz_id);
CREATE INDEX idx_questions_sort ON questions(quiz_id, sort_order);

-- JSONB misol:
-- options: ["Toshkent", "Samarqand", "Buxoro", "Namangan"]
-- correct_indices: {0}  → Toshkent to'g'ri
```

---

## 8. Import Logs (ai-engine xizmati)

```sql
CREATE TABLE import_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    quiz_id UUID REFERENCES quizzes(id),
    file_name VARCHAR(500) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,             -- SHA256 (dublikat uchun)
    file_size INTEGER,                          -- bytes
    file_type VARCHAR(20) NOT NULL,             -- docx, pdf, xlsx, png, txt
    status VARCHAR(20) NOT NULL,                -- processing, completed, failed, review
    total_detected INTEGER DEFAULT 0,           -- nechta savol topildi
    total_imported INTEGER DEFAULT 0,           -- nechta DB ga yozildi
    total_failed INTEGER DEFAULT 0,             -- nechta xato
    error_message TEXT,
    processing_time_ms INTEGER,                 -- qancha vaqt ketdi
    created_at TIMESTAMP DEFAULT now(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_import_user ON import_logs(user_id);
CREATE INDEX idx_import_hash ON import_logs(file_hash);
CREATE INDEX idx_import_status ON import_logs(status);
```

---

## 9. Games va Answers (game xizmati)

```sql
CREATE TABLE games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id),
    quiz_set_id UUID NOT NULL REFERENCES quiz_sets(id),  -- qaysi set
    user_id UUID NOT NULL REFERENCES users(id),
    mode VARCHAR(20) DEFAULT 'solo',            -- solo, telegram_group
    status VARCHAR(20) DEFAULT 'active',        -- active, paused, stopped, completed
    total_questions INTEGER NOT NULL,
    current_question_index INTEGER DEFAULT 0,   -- hozir nechanchi savolda
    correct_answers INTEGER DEFAULT 0,
    wrong_answers INTEGER DEFAULT 0,
    skipped_answers INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    time_spent_seconds INTEGER DEFAULT 0,
    is_retry BOOLEAN DEFAULT false,             -- xatolarni qayta ishlash
    parent_game_id UUID REFERENCES games(id),   -- retry bo'lsa — asl game
    started_at TIMESTAMP DEFAULT now(),
    paused_at TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE INDEX idx_games_user ON games(user_id);
CREATE INDEX idx_games_quiz ON games(quiz_id);
CREATE INDEX idx_games_set ON games(quiz_set_id);
CREATE INDEX idx_games_status ON games(status);
CREATE INDEX idx_games_user_status ON games(user_id, status);

CREATE TABLE answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(id),
    user_id UUID NOT NULL REFERENCES users(id),
    selected_indices INTEGER[],                  -- null = javob bermagan (skip)
    is_correct BOOLEAN,                          -- null = skip
    time_spent_ms INTEGER,                       -- savol uchun ketgan vaqt
    answered_at TIMESTAMP DEFAULT now()
) PARTITION BY RANGE (answered_at);

-- Oylik partition (million qator uchun)
CREATE TABLE answers_2026_05 PARTITION OF answers
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE answers_2026_06 PARTITION OF answers
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

CREATE INDEX idx_answers_game ON answers(game_id);
CREATE INDEX idx_answers_user ON answers(user_id);
CREATE INDEX idx_answers_wrong ON answers(game_id, is_correct) WHERE is_correct = false;
```

---

## 10. Gamification — XP, Daraja, Yutuq, Streak (game xizmati)

```sql
CREATE TABLE user_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    total_xp INTEGER DEFAULT 0,
    level VARCHAR(20) DEFAULT 'beginner',     -- beginner, learner, expert, master, professor, academic
    total_games INTEGER DEFAULT 0,
    total_correct INTEGER DEFAULT 0,
    total_wrong INTEGER DEFAULT 0,
    accuracy DECIMAL(5,2) DEFAULT 0,          -- foiz
    current_streak INTEGER DEFAULT 0,         -- hozirgi streak
    longest_streak INTEGER DEFAULT 0,         -- eng uzun streak
    last_played_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_user_stats_xp ON user_stats(total_xp DESC);
CREATE INDEX idx_user_stats_streak ON user_stats(current_streak DESC);

-- XP tarixi (qanday XP yutilgan)
CREATE TABLE xp_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    amount INTEGER NOT NULL,                  -- +10, +25, +50 ...
    reason VARCHAR(50) NOT NULL,              -- quiz_complete, perfect_score, streak, referral, achievement
    reference_id UUID,                        -- game_id yoki referral_id
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_xp_logs_user ON xp_logs(user_id);

-- Yutuqlar ro'yxati
CREATE TABLE achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,        -- 'first_quiz', '7_day_streak', 'perfect_score'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(50),                          -- emoji
    xp_reward INTEGER DEFAULT 0,              -- yutuq uchun XP
    condition_type VARCHAR(50) NOT NULL,       -- games_count, streak_days, accuracy, etc.
    condition_value INTEGER NOT NULL,          -- 1, 7, 100, etc.
    created_at TIMESTAMP DEFAULT now()
);

-- User yutuqlari
CREATE TABLE user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    achievement_id UUID NOT NULL REFERENCES achievements(id),
    unlocked_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX idx_user_achievements_unique ON user_achievements(user_id, achievement_id);
CREATE INDEX idx_user_achievements_user ON user_achievements(user_id);
```

---

## 11. Referal Tizimi (bot xizmati)

```sql
CREATE TABLE referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES users(id),    -- taklif qilgan
    referred_id UUID NOT NULL REFERENCES users(id),    -- taklif bo'yicha kelgan
    bonus_given BOOLEAN DEFAULT false,                  -- mukofot berilganmi
    bonus_days INTEGER DEFAULT 3,                       -- necha kun premium berildi
    created_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX idx_referrals_unique ON referrals(referrer_id, referred_id);
CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);
```

---

## 12. Telegram Guruh Sozlamalari (bot xizmati)

```sql
-- Telegram chat guruhlarida bot sozlamalari
CREATE TABLE telegram_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id BIGINT UNIQUE NOT NULL,              -- Telegram chat ID
    title VARCHAR(255),
    added_by UUID REFERENCES users(id),          -- kim qo'shgan
    voting_enabled BOOLEAN DEFAULT true,         -- quiz boshlash uchun voting
    min_voters INTEGER DEFAULT 3,                -- min qatnashchilar soni
    voting_timeout INTEGER DEFAULT 60,           -- voting kutish vaqti (soniya)
    who_can_start VARCHAR(20) DEFAULT 'admin',   -- admin, everyone
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_telegram_groups_chat ON telegram_groups(chat_id);
```

---

## 13. Leaderboards (game xizmati)

```sql
CREATE TABLE leaderboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    tag_id UUID REFERENCES tags(id),             -- null = umumiy, boshqasi = teg bo'yicha
    period VARCHAR(20) NOT NULL,                  -- daily, weekly, monthly, alltime
    period_key VARCHAR(20) NOT NULL,              -- '2026-05-16', '2026-W20', '2026-05'
    total_games INTEGER DEFAULT 0,
    total_correct INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    accuracy DECIMAL(5,2) DEFAULT 0,
    rank INTEGER,
    updated_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX idx_leaderboard_unique
    ON leaderboards(user_id, tag_id, period, period_key);
CREATE INDEX idx_leaderboard_rank
    ON leaderboards(period, period_key, total_score DESC);
```

---

## 14. Notifications (notifier xizmati)

```sql
CREATE TABLE notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,          -- 'quiz_ready', 'daily_reminder', 'new_quiz_in_group'
    text_uz TEXT NOT NULL,
    text_ru TEXT,
    text_en TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    template_id UUID REFERENCES notification_templates(id),
    custom_text TEXT,
    reference_type VARCHAR(50),                 -- 'quiz_group', 'achievement', 'referral'
    reference_id UUID,                          -- quiz_group_id, achievement_id, ...
    status VARCHAR(20) DEFAULT 'pending',       -- pending, sent, failed
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_user ON notifications(user_id);
```

---

## 15. Admin (admin-api xizmati)

```sql
CREATE TABLE admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    role VARCHAR(20) DEFAULT 'moderator',        -- superadmin, admin, moderator
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT now()
);
```

---

## Jadvallar Xaritasi

```
┌─────────────────┬───────────────────────────────────────────────────────────┐
│ Xizmat          │ O'z jadvallari                                            │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ bot             │ users, quiz_groups, quiz_group_subscribers,               │
│                 │ referrals, telegram_groups                                │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ subscription    │ plans, subscriptions, payments, usage_logs                │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ ai-engine       │ tags, quizzes, quiz_tags, quiz_sets, questions,           │
│                 │ import_logs                                               │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ game            │ games, answers, user_stats, xp_logs, achievements,       │
│                 │ user_achievements, leaderboards                           │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ notifier        │ notification_templates, notifications                     │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ admin-api       │ admins, settings                                          │
└─────────────────┴───────────────────────────────────────────────────────────┘

QOIDA: Xizmat faqat O'Z jadvallariga yozadi.
       Boshqa xizmat jadvalidan o'qish kerak → API orqali.
```

---

## Migration va Versiya

```
shared/migrations/ papkasida barcha migration lar saqlanadi.
Tool: Alembic (Python)

Har bir migration fayli:
├── Nomlash: 001_create_users.sql, 002_create_plans.sql ...
├── UP (yaratish) va DOWN (qaytarish) bo'lishi shart
└── Production da DOWN ishlatish TAQIQLANGAN

Yangi jadval/ustun qo'shish → yangi migration yozish.
Mavjud ustunni o'chirish → avval deprecated qilish, keyingi relizda o'chirish.
```

---

## Redis Ishlatilishi

```
Redis DB 0: Cache
├── user:{telegram_id}         → user ma'lumotlari (TTL: 1 soat)
├── quiz:{quiz_id}             → quiz + savollar (TTL: 30 min)
├── quiz_group:{slug}          → guruh ma'lumotlari (TTL: 30 min)
├── trending_tags              → eng ko'p ishlatiladigan teglar (TTL: 1 soat)
└── leaderboard:{period}:{key} → sorted set

Redis DB 1: Sessions
├── session:{user_id}          → hozirgi holat (state machine)
├── game:{game_id}             → active game state (qaysi savol, score)
└── voting:{chat_id}:{msg_id}  → Telegram guruh voting holati

Redis DB 2: Queue
├── Celery tasks (ai-engine)
└── Notification queue
```

---

## XP Daraja Jadvali (Reference)

```
Level hisoblash: user_stats.total_xp ga qarab

┌──────────┬──────────────┬─────────────┐
│ XP       │ Daraja       │ Icon        │
├──────────┼──────────────┼─────────────┤
│ 0-100    │ beginner     │ 🌱          │
│ 101-500  │ learner      │ 📗          │
│ 501-2000 │ expert       │ 📘          │
│ 2001-5000│ master       │ 📙          │
│ 5001-15k │ professor    │ 📕          │
│ 15001+   │ academic     │ 👑          │
└──────────┴──────────────┴─────────────┘
```
