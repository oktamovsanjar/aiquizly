package achievement

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/quiz-bot/game/db"
)

// CheckResult — yangi ochilgan yutuq
type CheckResult struct {
	AchievementSlug string
	AchievementName string
	XPReward        int
}

// achievementCondition — yutuq sharti tekshiruvi
type achievementCondition struct {
	slug  string
	check func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error)
}

var conditions = []achievementCondition{
	{
		slug: "first_quiz",
		check: func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
			return stats.TotalGames >= 1, nil
		},
	},
	{
		slug: "7_day_streak",
		check: func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
			return stats.CurrentStreak >= 7, nil
		},
	},
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
	{
		slug: "top_10",
		check: func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
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
			return rank > 0 && rank <= 10, nil
		},
	},
	{
		slug: "1000_questions",
		check: func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
			return stats.TotalCorrect+stats.TotalWrong >= 1000, nil
		},
	},
	{
		slug: "academic_level",
		check: func(ctx context.Context, q *db.Queries, userID uuid.UUID, stats *db.UserStats, event string) (bool, error) {
			return stats.Level == "academic", nil
		},
	},
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
			XPReward:        ach.XPReward,
		})
	}

	return results, nil
}
