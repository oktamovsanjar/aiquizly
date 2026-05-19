package leaderboard

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

const (
	PeriodDaily   = "daily"
	PeriodWeekly  = "weekly"
	PeriodMonthly = "monthly"
	PeriodAllTime = "alltime"

	TopN = 5 // bildirishnoma uchun top chegarasi
)

type LeaderboardEntry struct {
	UserID string
	Score  float64
	Rank   int64
}

// RankChange — o'rin o'zgarishi natijasi
type RankChange struct {
	OldRank  int64
	NewRank  int64
	InTop    bool // top N ga kirdi
	OutTop   bool // top N dan chiqdi
	Demoted  bool // o'rni pasaydi (top N ichida)
}

type Service struct {
	redis *redis.Client
}

func New(redisClient *redis.Client) *Service {
	return &Service{redis: redisClient}
}

// AddScore — alltime uchun ZADD (set), kunlik/haftalik uchun ZIncrBy (qo'shish)
func (s *Service) AddScore(ctx context.Context, userID string, totalXP float64, sessionScore float64) error {
	now := time.Now()

	pipe := s.redis.Pipeline()

	// Alltime: to'liq XP ni set qilamiz (har safar yangilaydi)
	pipe.ZAdd(ctx, "leaderboard:alltime", redis.Z{Score: totalXP, Member: userID})

	// Kunlik/haftalik/oylik: faqat bu sessiya ballini qo'shamiz
	dailyKey := fmt.Sprintf("leaderboard:%s:%s", PeriodDaily, now.Format("2006-01-02"))
	weeklyKey := fmt.Sprintf("leaderboard:%s:%s", PeriodWeekly, isoWeek(now))
	monthlyKey := fmt.Sprintf("leaderboard:%s:%s", PeriodMonthly, now.Format("2006-01"))

	pipe.ZIncrBy(ctx, dailyKey, sessionScore, userID)
	pipe.Expire(ctx, dailyKey, 48*time.Hour)
	pipe.ZIncrBy(ctx, weeklyKey, sessionScore, userID)
	pipe.Expire(ctx, weeklyKey, 14*24*time.Hour)
	pipe.ZIncrBy(ctx, monthlyKey, sessionScore, userID)

	_, err := pipe.Exec(ctx)
	return err
}

// UpdateAllAndCheck — ballarni yangilaydi va reyting o'zgarishini qaytaradi
func (s *Service) UpdateAllAndCheck(ctx context.Context, userID uuid.UUID, totalXP int, sessionXP int) (*RankChange, error) {
	uid := userID.String()

	// Yangilashdan oldingi o'rinni olish
	oldRank, _, oldErr := s.GetUserRank(ctx, "all", "alltime", uid)

	if err := s.AddScore(ctx, uid, float64(totalXP), float64(sessionXP)); err != nil {
		return nil, err
	}

	// Yangi o'rinni olish
	newRank, _, newErr := s.GetUserRank(ctx, "all", "alltime", uid)
	if newErr != nil {
		return nil, nil
	}

	change := &RankChange{NewRank: newRank}
	if oldErr == nil {
		change.OldRank = oldRank
	} else {
		change.OldRank = 0 // yangi foydalanuvchi
	}

	// O'zgarishlarni aniqlash
	wasInTop := change.OldRank > 0 && change.OldRank <= TopN
	isInTop := newRank <= TopN

	change.InTop = !wasInTop && isInTop
	change.OutTop = wasInTop && !isInTop
	change.Demoted = wasInTop && isInTop && newRank > change.OldRank

	return change, nil
}

// UpdateAll — barcha periodlar uchun leaderboard ni yangilaydi
func (s *Service) UpdateAll(ctx context.Context, userID uuid.UUID, totalXP int, correct int, games int, accuracy float64) error {
	_, err := s.UpdateAllAndCheck(ctx, userID, totalXP, totalXP)
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

// Notification — Redis queue ga yuboriladigan xabar
type Notification struct {
	UserTelegramID int64         `json:"user_telegram_id"`
	Text           string        `json:"text"`
	ParseMode      string        `json:"parse_mode,omitempty"`
	InlineButtons  []InlineBtn   `json:"inline_buttons,omitempty"`
}

type InlineBtn struct {
	Text string `json:"text"`
	URL  string `json:"url,omitempty"`
}

// PushNotification — notifier queue ga xabar qo'shadi
func (s *Service) PushNotification(ctx context.Context, telegramID int64, text string, buttons []InlineBtn) error {
	n := Notification{
		UserTelegramID: telegramID,
		Text:           text,
		ParseMode:      "HTML",
		InlineButtons:  buttons,
	}
	data, err := json.Marshal(n)
	if err != nil {
		return err
	}
	return s.redis.RPush(ctx, "notification:queue", data).Err()
}

func isoWeek(t time.Time) string {
	year, week := t.ISOWeek()
	return fmt.Sprintf("%d-W%02d", year, week)
}
