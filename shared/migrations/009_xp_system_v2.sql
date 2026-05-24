-- 009_xp_system_v2.sql
-- XP / Level / Gamifikatsiya tizimi v2 (100 levelli, kvadratik formula)
-- Foydalanuvchi qarori: to'liq qayta hisoblash, kunlik XP limit yo'q.

-- ──────────────────────────────────────────────────────────────────────
-- 1. user_stats ga level_num ustuni
-- ──────────────────────────────────────────────────────────────────────
ALTER TABLE user_stats
    ADD COLUMN IF NOT EXISTS level_num INTEGER NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_user_stats_level_num ON user_stats(level_num DESC);

-- ──────────────────────────────────────────────────────────────────────
-- 2. Backfill: total_xp dan level_num ni hisoblash
-- Formula teskari: N = (xp/50)^(1/1.7)
-- ──────────────────────────────────────────────────────────────────────
UPDATE user_stats
SET level_num = GREATEST(1, LEAST(100,
    FLOOR(POW(GREATEST(total_xp, 0) / 50.0, 1.0/1.7))::INTEGER + 1
))
WHERE TRUE;

-- Eslatma: floor(...)+1 chunki Lvl N = XPForLevel(N) dan boshlanadi
-- DetermineLevelNum logic: agar XP >= XPForLevel(N), Lvl N
-- e.g. XP=2506 -> floor((2506/50)^(1/1.7)) = floor(50.12^0.588) = floor(9.99) = 9, +1 = 10 ✓

-- ──────────────────────────────────────────────────────────────────────
-- 3. level (varchar) ustunini yangi tier slugga remap qilish
-- ──────────────────────────────────────────────────────────────────────
UPDATE user_stats
SET level = CASE
    WHEN level_num <= 10  THEN 'beginner'
    WHEN level_num <= 20  THEN 'student'
    WHEN level_num <= 30  THEN 'expert'
    WHEN level_num <= 40  THEN 'skilled'
    WHEN level_num <= 50  THEN 'experienced'
    WHEN level_num <= 60  THEN 'mentor'
    WHEN level_num <= 70  THEN 'sage'
    WHEN level_num <= 80  THEN 'professor'
    WHEN level_num <= 90  THEN 'academic'
    WHEN level_num <= 99  THEN 'legendary'
    ELSE 'legend'
END;

-- ──────────────────────────────────────────────────────────────────────
-- 4. Mavjud yutuq nomlarini O'zbek tilida tasdiqlash (idempotent)
-- ──────────────────────────────────────────────────────────────────────
UPDATE achievements SET name = '7 kunlik streak'   WHERE slug = '7_day_streak';
UPDATE achievements SET name = 'Birinchi quiz'     WHERE slug = 'first_quiz';
UPDATE achievements SET name = 'Mukammal natija'  WHERE slug = 'perfect_score';
UPDATE achievements SET name = 'Birinchi yuklash' WHERE slug = 'first_upload';
UPDATE achievements SET name = 'Haftalik Top-10'  WHERE slug = 'top_10';
UPDATE achievements SET name = '1000 savol'        WHERE slug = '1000_questions';
UPDATE achievements SET name = 'Akademik daraja'  WHERE slug = 'academic_level';

-- ──────────────────────────────────────────────────────────────────────
-- 5. 17 ta yangi yutuq
-- ──────────────────────────────────────────────────────────────────────
INSERT INTO achievements (slug, name, description, icon, xp_reward, condition_type, condition_value) VALUES
    -- Streak ladder
    ('streak_3',     '3 kunlik streak',     'Ketma-ket 3 kun o''yna',                '🔥',     30,   'streak_days',   3),
    ('streak_14',    '14 kunlik streak',    'Ketma-ket 2 hafta',                     '🔥🔥',   100,  'streak_days',   14),
    ('streak_30',    '30 kunlik streak',    'Ketma-ket 1 oy',                        '🔥🔥🔥', 300,  'streak_days',   30),
    ('streak_100',   '100 kunlik streak',   'Ketma-ket 100 kun — afsona',            '🌋',     1500, 'streak_days',   100),
    -- Game count ladder
    ('games_10',     '10 quiz',             '10 ta quiz yechdingiz',                 '🎮',     50,   'games_count',   10),
    ('games_50',     '50 quiz',             '50 ta quiz yechdingiz',                 '🎮',     200,  'games_count',   50),
    ('games_100',    '100 quiz',            '100 ta quiz yetib bo''ldi',             '🎯',     500,  'games_count',   100),
    ('games_500',    '500 quiz',            'Quiz ustasi — 500 ta',                  '🏆',     2000, 'games_count',   500),
    -- Perfect score ladder
    ('perfect_10',   '10 ta mukammal',      '10 ta quizni 100% yechdingiz',          '💯',     200,  'perfect_count', 10),
    ('perfect_100',  'Mukammallik ustasi',  '100 ta mukammal natija',                '👑',     1500, 'perfect_count', 100),
    -- Level milestones
    ('level_10',     'Talaba',              'Lvl 10 ga yetdingiz',                   '📗',     100,  'level_num',     10),
    ('level_25',     'Bilimdon',            'Lvl 25 ga yetdingiz',                   '📘',     300,  'level_num',     25),
    ('level_50',     'Ustoz',               'Lvl 50 ga yetdingiz',                   '🎓',     1000, 'level_num',     50),
    ('level_75',     'Professor',           'Lvl 75 ga yetdingiz',                   '🏛',     2500, 'level_num',     75),
    ('level_100',    'Legenda',             'Lvl 100 — eng yuqori daraja',           '🏆',     10000,'level_num',     100),
    -- Speed / faollik
    ('marathon_day', '10 quiz bir kunda',   'Bir kunda 10 ta quiz yechdingiz',       '⚡',     200,  'games_in_day',  10),
    ('weekly_top_3', 'Haftalik Top-3',      'Hafta yakuni top 3 ga kirdingiz',       '🥉',     500,  'weekly_top',    3)
ON CONFLICT (slug) DO NOTHING;
