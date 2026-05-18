-- Migration 008: telegram_groups ga linked_quiz_id va who_can_start default o'zgarishi

ALTER TABLE telegram_groups
    ADD COLUMN IF NOT EXISTS linked_quiz_id VARCHAR(36) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS stop_min_voters INTEGER NOT NULL DEFAULT 3;

-- who_can_start default ni 'all' ga o'zgartirish
ALTER TABLE telegram_groups
    ALTER COLUMN who_can_start SET DEFAULT 'all';

-- Mavjud guruhlar ham 'all' ga o'tkazilsin
UPDATE telegram_groups SET who_can_start = 'all' WHERE who_can_start = 'admin';
