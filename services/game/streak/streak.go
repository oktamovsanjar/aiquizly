package streak

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/quiz-bot/game/db"
)

// UpdateStreak — foydalanuvchi streakini yangilaydi
// Agar bugun hali o'ynamagan bo'lsa +1
// Agar kecha o'ynamagan bo'lsa reset to 1
// Agar bugun o'ynagan bo'lsa unchanged
// Qaytaradi: yangi streak qiymati
func UpdateStreak(ctx context.Context, pool *pgxpool.Pool, userID uuid.UUID) (int, error) {
	q := db.NewQueries(pool)

	stats, err := q.GetUserStats(ctx, userID)
	if err != nil && err != db.ErrNotFound {
		return 0, err
	}

	now := time.Now()
	today := now.Truncate(24 * time.Hour)

	if stats == nil || err == db.ErrNotFound {
		// Yangi foydalanuvchi — birinchi o'yin
		newStreak := 1
		lastPlayed := now
		upsertParams := db.UpsertUserStatsParams{
			UserID:        userID,
			TotalXP:       0,
			Level:         "beginner",
			LevelNum:      1,
			TotalGames:    0,
			TotalCorrect:  0,
			TotalWrong:    0,
			Accuracy:      0,
			CurrentStreak: newStreak,
			LongestStreak: newStreak,
			LastPlayedAt:  &lastPlayed,
		}
		if err := q.UpsertUserStats(ctx, upsertParams); err != nil {
			return 0, err
		}
		return newStreak, nil
	}

	var newStreak int

	if stats.LastPlayedAt == nil {
		// Hech qachon o'ynamagan
		newStreak = 1
	} else {
		lastPlayedDay := stats.LastPlayedAt.Truncate(24 * time.Hour)
		yesterday := today.Add(-24 * time.Hour)

		if lastPlayedDay.Equal(today) {
			// Bugun allaqachon o'ynagan — o'zgarmaydi
			return stats.CurrentStreak, nil
		} else if lastPlayedDay.Equal(yesterday) {
			// Kecha o'ynagan — streak +1
			newStreak = stats.CurrentStreak + 1
		} else {
			// Kecha o'ynamagan — reset
			newStreak = 1
		}
	}

	longestStreak := stats.LongestStreak
	if newStreak > longestStreak {
		longestStreak = newStreak
	}

	lastPlayed := now
	upsertParams := db.UpsertUserStatsParams{
		UserID:        userID,
		TotalXP:       stats.TotalXP,
		Level:         stats.Level,
		LevelNum:      stats.LevelNum,
		TotalGames:    stats.TotalGames,
		TotalCorrect:  stats.TotalCorrect,
		TotalWrong:    stats.TotalWrong,
		Accuracy:      stats.Accuracy,
		CurrentStreak: newStreak,
		LongestStreak: longestStreak,
		LastPlayedAt:  &lastPlayed,
	}
	if err := q.UpsertUserStats(ctx, upsertParams); err != nil {
		return 0, err
	}

	return newStreak, nil
}

// ShouldAwardStreakBonus — milestone streak uchun XP bonusini qaytaradi
// Milestone streaklar: 7, 14, 30, 60, 100 kun (yangilangan — Faza 2)
func ShouldAwardStreakBonus(streakDays int) int {
	switch {
	case streakDays == 100:
		return 1000 // afsonaviy
	case streakDays >= 60 && streakDays%60 == 0:
		return 300
	case streakDays >= 30 && streakDays%30 == 0:
		return 150
	case streakDays >= 14 && streakDays%14 == 0:
		return 50
	case streakDays >= 7 && streakDays%7 == 0:
		return 20
	default:
		return 0
	}
}
