package leaderboard

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

// Period konstantalari
const (
	PeriodDaily   = "daily"
	PeriodWeekly  = "weekly"
	PeriodMonthly = "monthly"
	PeriodAllTime = "alltime"
)

type LeaderboardEntry struct {
	UserID string
	Score  float64
	Rank   int64
}

type Service struct {
	redis *redis.Client
}

func New(redisClient *redis.Client) *Service {
	return &Service{redis: redisClient}
}

// AddScore — foydalanuvchi balini leaderboard ga qo'shadi
func (s *Service) AddScore(ctx context.Context, userID string, score float64) error {
	now := time.Now()

	periods := map[string]string{
		PeriodDaily:   fmt.Sprintf("%s:%s", PeriodDaily, now.Format("2006-01-02")),
		PeriodWeekly:  fmt.Sprintf("%s:%s", PeriodWeekly, isoWeek(now)),
		PeriodMonthly: fmt.Sprintf("%s:%s", PeriodMonthly, now.Format("2006-01")),
		PeriodAllTime: PeriodAllTime,
	}

	pipe := s.redis.Pipeline()
	for _, key := range periods {
		redisKey := fmt.Sprintf("leaderboard:%s", key)
		pipe.ZIncrBy(ctx, redisKey, score, userID)
		// Daily va weekly uchun TTL qo'yish
		if key[:5] == PeriodDaily {
			pipe.Expire(ctx, redisKey, 48*time.Hour)
		} else if key[:6] == PeriodWeekly {
			pipe.Expire(ctx, redisKey, 14*24*time.Hour)
		}
	}
	_, err := pipe.Exec(ctx)
	return err
}

// GetTopN — eng yaxshi N ta o'yinchini qaytaradi
func (s *Service) GetTopN(ctx context.Context, period, periodKey string, n int) ([]LeaderboardEntry, error) {
	var key string
	if periodKey == "alltime" {
		key = "leaderboard:alltime"
	} else {
		key = fmt.Sprintf("leaderboard:%s:%s", period, periodKey)
	}

	results, err := s.redis.ZRevRangeWithScores(ctx, key, 0, int64(n-1)).Result()
	if err != nil {
		return nil, err
	}

	entries := make([]LeaderboardEntry, len(results))
	for i, r := range results {
		entries[i] = LeaderboardEntry{
			UserID: r.Member.(string),
			Score:  r.Score,
			Rank:   int64(i + 1),
		}
	}
	return entries, nil
}

// UpdateAll — barcha periodlar uchun leaderboard ni yangilaydi (handlers.LeaderboardUpdater interfeysi uchun)
func (s *Service) UpdateAll(ctx context.Context, userID uuid.UUID, score int, correct int, games int, accuracy float64) error {
	return s.AddScore(ctx, userID.String(), float64(score))
}

// GetUserRank — foydalanuvchining reytingdagi o'rnini qaytaradi
func (s *Service) GetUserRank(ctx context.Context, period, periodKey, userID string) (int64, float64, error) {
	var key string
	if periodKey == "alltime" {
		key = "leaderboard:alltime"
	} else {
		key = fmt.Sprintf("leaderboard:%s:%s", period, periodKey)
	}

	rank, err := s.redis.ZRevRank(ctx, key, userID).Result()
	if err != nil {
		return 0, 0, err
	}
	score, err := s.redis.ZScore(ctx, key, userID).Result()
	if err != nil {
		return 0, 0, err
	}
	return rank + 1, score, nil
}

func isoWeek(t time.Time) string {
	year, week := t.ISOWeek()
	return fmt.Sprintf("%d-W%02d", year, week)
}
