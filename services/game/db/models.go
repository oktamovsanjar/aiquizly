package db

import (
	"time"

	"github.com/google/uuid"
)

// Game — games jadvali
type Game struct {
	ID                   uuid.UUID  `json:"id"`
	QuizID               uuid.UUID  `json:"quiz_id"`
	QuizSetID            uuid.UUID  `json:"quiz_set_id"`
	UserID               uuid.UUID  `json:"user_id"`
	Mode                 string     `json:"mode"`
	Status               string     `json:"status"`
	TotalQuestions       int        `json:"total_questions"`
	CurrentQuestionIndex int        `json:"current_question_index"`
	CorrectAnswers       int        `json:"correct_answers"`
	WrongAnswers         int        `json:"wrong_answers"`
	SkippedAnswers       int        `json:"skipped_answers"`
	Score                int        `json:"score"`
	TimeSpentSeconds     int        `json:"time_spent_seconds"`
	IsRetry              bool       `json:"is_retry"`
	ParentGameID         *uuid.UUID `json:"parent_game_id,omitempty"`
	StartedAt            time.Time  `json:"started_at"`
	PausedAt             *time.Time `json:"paused_at,omitempty"`
	FinishedAt           *time.Time `json:"finished_at,omitempty"`
}

// Answer — answers jadvali
type Answer struct {
	ID              uuid.UUID `json:"id"`
	GameID          uuid.UUID `json:"game_id"`
	QuestionID      uuid.UUID `json:"question_id"`
	UserID          uuid.UUID `json:"user_id"`
	SelectedIndices []int     `json:"selected_indices"`
	IsCorrect       *bool     `json:"is_correct"`
	TimeSpentMs     int       `json:"time_spent_ms"`
	AnsweredAt      time.Time `json:"answered_at"`
}

// UserStats — user_stats jadvali
type UserStats struct {
	ID            uuid.UUID  `json:"id"`
	UserID        uuid.UUID  `json:"user_id"`
	TotalXP       int        `json:"total_xp"`
	Level         string     `json:"level"`
	TotalGames    int        `json:"total_games"`
	TotalCorrect  int        `json:"total_correct"`
	TotalWrong    int        `json:"total_wrong"`
	Accuracy      float64    `json:"accuracy"`
	CurrentStreak int        `json:"current_streak"`
	LongestStreak int        `json:"longest_streak"`
	LastPlayedAt  *time.Time `json:"last_played_at,omitempty"`
	UpdatedAt     time.Time  `json:"updated_at"`
}

// XPLog — xp_logs jadvali
type XPLog struct {
	ID          uuid.UUID  `json:"id"`
	UserID      uuid.UUID  `json:"user_id"`
	Amount      int        `json:"amount"`
	Reason      string     `json:"reason"`
	ReferenceID *uuid.UUID `json:"reference_id,omitempty"`
	CreatedAt   time.Time  `json:"created_at"`
}

// Achievement — achievements jadvali
type Achievement struct {
	ID             uuid.UUID `json:"id"`
	Slug           string    `json:"slug"`
	Name           string    `json:"name"`
	Description    string    `json:"description"`
	Icon           string    `json:"icon"`
	XPReward       int       `json:"xp_reward"`
	ConditionType  string    `json:"condition_type"`
	ConditionValue int       `json:"condition_value"`
	CreatedAt      time.Time `json:"created_at"`
}

// UserAchievement — user_achievements jadvali
type UserAchievement struct {
	ID            uuid.UUID    `json:"id"`
	UserID        uuid.UUID    `json:"user_id"`
	AchievementID uuid.UUID    `json:"achievement_id"`
	UnlockedAt    time.Time    `json:"unlocked_at"`
	Achievement   *Achievement `json:"achievement,omitempty"`
}

// LeaderboardEntry — leaderboards jadvali
type LeaderboardEntry struct {
	ID           uuid.UUID  `json:"id"`
	UserID       uuid.UUID  `json:"user_id"`
	TagID        *uuid.UUID `json:"tag_id,omitempty"`
	Period       string     `json:"period"`
	PeriodKey    string     `json:"period_key"`
	TotalGames   int        `json:"total_games"`
	TotalCorrect int        `json:"total_correct"`
	TotalScore   int        `json:"total_score"`
	Accuracy     float64    `json:"accuracy"`
	Rank         int        `json:"rank"`
	UpdatedAt    time.Time  `json:"updated_at"`
}

// CreateGameParams — yangi game yaratish uchun parametrlar
type CreateGameParams struct {
	QuizID         uuid.UUID
	QuizSetID      uuid.UUID
	UserID         uuid.UUID
	Mode           string
	TotalQuestions int
	IsRetry        bool
	ParentGameID   *uuid.UUID
}

// UpdateGameParams — game yangilash uchun parametrlar
type UpdateGameParams struct {
	Status               string
	CurrentQuestionIndex int
	CorrectAnswers       int
	WrongAnswers         int
	SkippedAnswers       int
	Score                int
	TimeSpentSeconds     int
	PausedAt             *time.Time
	FinishedAt           *time.Time
}

// SaveAnswerParams — javob saqlash uchun parametrlar
type SaveAnswerParams struct {
	GameID          uuid.UUID
	QuestionID      uuid.UUID
	UserID          uuid.UUID
	SelectedIndices []int
	IsCorrect       *bool
	TimeSpentMs     int
}

// UpsertUserStatsParams — user statistikasini yangilash uchun parametrlar
type UpsertUserStatsParams struct {
	UserID        uuid.UUID
	TotalXP       int
	Level         string
	TotalGames    int
	TotalCorrect  int
	TotalWrong    int
	Accuracy      float64
	CurrentStreak int
	LongestStreak int
	LastPlayedAt  *time.Time
}

// AddXPLogParams — XP log qo'shish uchun parametrlar
type AddXPLogParams struct {
	UserID      uuid.UUID
	Amount      int
	Reason      string
	ReferenceID *uuid.UUID
}

// UpsertLeaderboardParams — leaderboard yangilash uchun parametrlar
type UpsertLeaderboardParams struct {
	UserID       uuid.UUID
	TagID        *uuid.UUID
	Period       string
	PeriodKey    string
	TotalGames   int
	TotalCorrect int
	TotalScore   int
	Accuracy     float64
}
