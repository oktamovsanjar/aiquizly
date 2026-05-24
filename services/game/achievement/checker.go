package achievement

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/quiz-bot/game/db"
	"github.com/quiz-bot/game/scoring"
)

// CheckResult — yangi ochilgan yutuq
type CheckResult struct {
	AchievementSlug string
	AchievementName string
	AchievementIcon string
	XPReward        int
}

// checkFn — yutuq sharti tekshiruvi
type checkFn func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error)

// achievementCondition — yutuq sharti tekshiruvi
type achievementCondition struct {
	slug  string
	check checkFn
}

// ─── Helper closures ────────────────────────────────────────────────

func streakAtLeast(n int) checkFn {
	return func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
		return stats.CurrentStreak >= n, nil
	}
}

func gamesAtLeast(n int) checkFn {
	return func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
		return stats.TotalGames >= n, nil
	}
}

func levelAtLeast(n int) checkFn {
	return func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
		return scoring.DetermineLevelNum(stats.TotalXP) >= n, nil
	}
}

func perfectAtLeast(n int) checkFn {
	return func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
		count, err := q.GetPerfectScoreCount(ctx, userID)
		if err != nil {
			return false, err
		}
		return count >= n, nil
	}
}

func gamesInLast24h(n int) checkFn {
	return func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
		count, err := q.GetGamesInLast24h(ctx, userID)
		if err != nil {
			return false, err
		}
		return count >= n, nil
	}
}

func weeklyTopAtMost(n int) checkFn {
	return func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
		now := time.Now()
		year, week := now.ISOWeek()
		periodKey := fmt.Sprintf("%d-W%02d", year, week)
		rank, err := q.GetUserWeeklyRank(ctx, userID, periodKey)
		if err != nil {
			if err == db.ErrNotFound {
				return false, nil
			}
			return false, err
		}
		return rank > 0 && rank <= n, nil
	}
}

func answersAtLeast(n int) checkFn {
	return func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
		return stats.TotalCorrect+stats.TotalWrong >= n, nil
	}
}

// ─── Yutuq shartlari ────────────────────────────────────────────────

var conditions = []achievementCondition{
	// Mavjud yutuqlar
	{slug: "first_quiz", check: gamesAtLeast(1)},
	{slug: "7_day_streak", check: streakAtLeast(7)},
	{
		slug: "perfect_score",
		check: func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
			return event == "perfect_score", nil
		},
	},
	{
		slug: "first_upload",
		check: func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
			if event == "quiz_created" {
				return true, nil
			}
			count, err := q.GetXPLogsCountByReason(ctx, userID, "quiz_complete")
			if err != nil {
				return false, err
			}
			return count >= 1, nil
		},
	},
	{slug: "top_10", check: weeklyTopAtMost(10)},
	{slug: "1000_questions", check: answersAtLeast(1000)},
	{slug: "academic_level", check: levelAtLeast(100)},

	// Yangi yutuqlar (Faza 4)
	{slug: "streak_3", check: streakAtLeast(3)},
	{slug: "streak_14", check: streakAtLeast(14)},
	{slug: "streak_30", check: streakAtLeast(30)},
	{slug: "streak_100", check: streakAtLeast(100)},

	{slug: "games_10", check: gamesAtLeast(10)},
	{slug: "games_50", check: gamesAtLeast(50)},
	{slug: "games_100", check: gamesAtLeast(100)},
	{slug: "games_500", check: gamesAtLeast(500)},

	{slug: "perfect_10", check: perfectAtLeast(10)},
	{slug: "perfect_100", check: perfectAtLeast(100)},

	{slug: "level_10", check: levelAtLeast(10)},
	{slug: "level_25", check: levelAtLeast(25)},
	{slug: "level_50", check: levelAtLeast(50)},
	{slug: "level_75", check: levelAtLeast(75)},
	{slug: "level_100", check: levelAtLeast(100)},

	{slug: "marathon_day", check: gamesInLast24h(10)},
	{slug: "weekly_top_3", check: weeklyTopAtMost(3)},
}

// Check — barcha yutuq shartlarini tekshiradi va yangi yutuqlarni ochadi
// Events: "game_complete", "perfect_score", "quiz_created", "share", "referral"
func Check(ctx context.Context, pool *pgxpool.Pool, userID uuid.UUID, stats *db.UserStats, event string) ([]CheckResult, error) {
	q := db.NewQueries(pool)

	// Foydalanuvchining mavjud yutuqlarini olish
	userAchievements, err := q.GetUserAchievements(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("foydalanuvchi yutuqlarini olishda xato: %w", err)
	}

	// Mavjud yutuqlar ID lari set
	unlockedIDs := make(map[uuid.UUID]bool)
	for _, ua := range userAchievements {
		unlockedIDs[ua.AchievementID] = true
	}

	var results []CheckResult

	for _, cond := range conditions {
		// Yutuqni olish
		ach, err := q.GetAchievementBySlug(ctx, cond.slug)
		if err != nil {
			if err == db.ErrNotFound {
				// Bu yutuq DB da yo'q, o'tkazib yuboramiz
				continue
			}
			return nil, fmt.Errorf("yutuqni olishda xato (%s): %w", cond.slug, err)
		}

		// Allaqachon ochilgan bo'lsa o'tkazib yuboramiz
		if unlockedIDs[ach.ID] {
			continue
		}

		// Shartni tekshirish
		met, err := cond.check(ctx, q, userID, stats, event)
		if err != nil {
			// Tekshiruv xatosi — o'tkazib yuboramiz
			continue
		}

		if !met {
			continue
		}

		// Yutuqni ochish
		if err := q.UnlockAchievement(ctx, userID, ach.ID); err != nil {
			return nil, fmt.Errorf("yutuqni ochishda xato (%s): %w", cond.slug, err)
		}

		results = append(results, CheckResult{
			AchievementSlug: ach.Slug,
			AchievementName: ach.Name,
			AchievementIcon: ach.Icon,
			XPReward:        ach.XPReward,
		})
	}

	return results, nil
}
