package db

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Queries — DB so'rovlari uchun wrapper
type Queries struct {
	pool *pgxpool.Pool
}

// NewQueries — Queries instansiyasi yaratadi
func NewQueries(pool *pgxpool.Pool) *Queries {
	return &Queries{pool: pool}
}

// Pool — pgxpool.Pool ni qaytaradi (streak va achievement uchun)
func (q *Queries) Pool() *pgxpool.Pool {
	return q.pool
}

// CreateGame — yangi game yozadi
func (q *Queries) CreateGame(ctx context.Context, p CreateGameParams) (*Game, error) {
	id := uuid.New()
	query := `
		INSERT INTO games (id, quiz_id, quiz_set_id, user_id, mode, status,
		                   total_questions, current_question_index, correct_answers,
		                   wrong_answers, skipped_answers, score, time_spent_seconds,
		                   is_retry, parent_game_id, started_at)
		VALUES ($1,$2,$3,$4,$5,'active',$6,0,0,0,0,0,0,$7,$8,now())
		RETURNING id, quiz_id, quiz_set_id, user_id, mode, status,
		          total_questions, current_question_index, correct_answers,
		          wrong_answers, skipped_answers, score, time_spent_seconds,
		          is_retry, parent_game_id, started_at, paused_at, finished_at`

	row := q.pool.QueryRow(ctx, query,
		id, p.QuizID, p.QuizSetID, p.UserID, p.Mode,
		p.TotalQuestions, p.IsRetry, p.ParentGameID,
	)

	return scanGame(row)
}

// GetGame — game_id bo'yicha o'yin ma'lumotlarini oladi
func (q *Queries) GetGame(ctx context.Context, gameID uuid.UUID) (*Game, error) {
	query := `
		SELECT id, quiz_id, quiz_set_id, user_id, mode, status,
		       total_questions, current_question_index, correct_answers,
		       wrong_answers, skipped_answers, score, time_spent_seconds,
		       is_retry, parent_game_id, started_at, paused_at, finished_at
		FROM games WHERE id = $1`

	row := q.pool.QueryRow(ctx, query, gameID)
	g, err := scanGame(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, err
	}
	return g, nil
}

// UpdateGame — game holatini yangilaydi
func (q *Queries) UpdateGame(ctx context.Context, gameID uuid.UUID, p UpdateGameParams) error {
	query := `
		UPDATE games SET
			status = $2,
			current_question_index = $3,
			correct_answers = $4,
			wrong_answers = $5,
			skipped_answers = $6,
			score = $7,
			time_spent_seconds = $8,
			paused_at = $9,
			finished_at = $10
		WHERE id = $1`

	_, err := q.pool.Exec(ctx, query,
		gameID,
		p.Status,
		p.CurrentQuestionIndex,
		p.CorrectAnswers,
		p.WrongAnswers,
		p.SkippedAnswers,
		p.Score,
		p.TimeSpentSeconds,
		p.PausedAt,
		p.FinishedAt,
	)
	return err
}

// GetActiveGame — foydalanuvchining faol o'yinini oladi
func (q *Queries) GetActiveGame(ctx context.Context, userID uuid.UUID) (*Game, error) {
	query := `
		SELECT id, quiz_id, quiz_set_id, user_id, mode, status,
		       total_questions, current_question_index, correct_answers,
		       wrong_answers, skipped_answers, score, time_spent_seconds,
		       is_retry, parent_game_id, started_at, paused_at, finished_at
		FROM games
		WHERE user_id = $1 AND status IN ('active','paused')
		ORDER BY started_at DESC
		LIMIT 1`

	row := q.pool.QueryRow(ctx, query, userID)
	g, err := scanGame(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, err
	}
	return g, nil
}

// SaveAnswer — javobni saqlaydi
func (q *Queries) SaveAnswer(ctx context.Context, p SaveAnswerParams) error {
	id := uuid.New()
	query := `
		INSERT INTO answers (id, game_id, question_id, user_id, selected_indices, is_correct, time_spent_ms, answered_at)
		VALUES ($1,$2,$3,$4,$5,$6,$7,now())`

	_, err := q.pool.Exec(ctx, query,
		id, p.GameID, p.QuestionID, p.UserID,
		p.SelectedIndices, p.IsCorrect, p.TimeSpentMs,
	)
	return err
}

// GetWrongAnswers — game dagi noto'g'ri javoblarni oladi
func (q *Queries) GetWrongAnswers(ctx context.Context, gameID uuid.UUID) ([]Answer, error) {
	query := `
		SELECT id, game_id, question_id, user_id, selected_indices, is_correct, time_spent_ms, answered_at
		FROM answers
		WHERE game_id = $1 AND is_correct = false
		ORDER BY answered_at`

	rows, err := q.pool.Query(ctx, query, gameID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var answers []Answer
	for rows.Next() {
		a, err := scanAnswer(rows)
		if err != nil {
			return nil, err
		}
		answers = append(answers, *a)
	}
	return answers, rows.Err()
}

// GetUserStats — foydalanuvchi statistikasini oladi
func (q *Queries) GetUserStats(ctx context.Context, userID uuid.UUID) (*UserStats, error) {
	query := `
		SELECT id, user_id, total_xp, level, total_games, total_correct, total_wrong,
		       accuracy, current_streak, longest_streak, last_played_at, updated_at
		FROM user_stats WHERE user_id = $1`

	row := q.pool.QueryRow(ctx, query, userID)
	s, err := scanUserStats(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, err
	}
	return s, nil
}

// UpsertUserStats — foydalanuvchi statistikasini yaratadi yoki yangilaydi
func (q *Queries) UpsertUserStats(ctx context.Context, p UpsertUserStatsParams) error {
	query := `
		INSERT INTO user_stats (id, user_id, total_xp, level, total_games, total_correct, total_wrong,
		                        accuracy, current_streak, longest_streak, last_played_at, updated_at)
		VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now())
		ON CONFLICT (user_id) DO UPDATE SET
			total_xp       = EXCLUDED.total_xp,
			level          = EXCLUDED.level,
			total_games    = EXCLUDED.total_games,
			total_correct  = EXCLUDED.total_correct,
			total_wrong    = EXCLUDED.total_wrong,
			accuracy       = EXCLUDED.accuracy,
			current_streak = EXCLUDED.current_streak,
			longest_streak = EXCLUDED.longest_streak,
			last_played_at = EXCLUDED.last_played_at,
			updated_at     = now()`

	_, err := q.pool.Exec(ctx, query,
		p.UserID, p.TotalXP, p.Level, p.TotalGames,
		p.TotalCorrect, p.TotalWrong, p.Accuracy,
		p.CurrentStreak, p.LongestStreak, p.LastPlayedAt,
	)
	return err
}

// AddXPLog — XP log yozadi
func (q *Queries) AddXPLog(ctx context.Context, p AddXPLogParams) error {
	id := uuid.New()
	query := `
		INSERT INTO xp_logs (id, user_id, amount, reason, reference_id, created_at)
		VALUES ($1,$2,$3,$4,$5,now())`

	_, err := q.pool.Exec(ctx, query, id, p.UserID, p.Amount, p.Reason, p.ReferenceID)
	return err
}

// GetAchievements — barcha yutuqlarni oladi
func (q *Queries) GetAchievements(ctx context.Context) ([]Achievement, error) {
	query := `
		SELECT id, slug, name, description, icon, xp_reward, condition_type, condition_value, created_at
		FROM achievements ORDER BY created_at`

	rows, err := q.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var achievements []Achievement
	for rows.Next() {
		var a Achievement
		err := rows.Scan(
			&a.ID, &a.Slug, &a.Name, &a.Description, &a.Icon,
			&a.XPReward, &a.ConditionType, &a.ConditionValue, &a.CreatedAt,
		)
		if err != nil {
			return nil, err
		}
		achievements = append(achievements, a)
	}
	return achievements, rows.Err()
}

// GetUserAchievements — foydalanuvchi yutuqlarini oladi
func (q *Queries) GetUserAchievements(ctx context.Context, userID uuid.UUID) ([]UserAchievement, error) {
	query := `
		SELECT ua.id, ua.user_id, ua.achievement_id, ua.unlocked_at,
		       a.id, a.slug, a.name, a.description, a.icon, a.xp_reward,
		       a.condition_type, a.condition_value, a.created_at
		FROM user_achievements ua
		JOIN achievements a ON a.id = ua.achievement_id
		WHERE ua.user_id = $1
		ORDER BY ua.unlocked_at DESC`

	rows, err := q.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []UserAchievement
	for rows.Next() {
		var ua UserAchievement
		var a Achievement
		err := rows.Scan(
			&ua.ID, &ua.UserID, &ua.AchievementID, &ua.UnlockedAt,
			&a.ID, &a.Slug, &a.Name, &a.Description, &a.Icon, &a.XPReward,
			&a.ConditionType, &a.ConditionValue, &a.CreatedAt,
		)
		if err != nil {
			return nil, err
		}
		ua.Achievement = &a
		results = append(results, ua)
	}
	return results, rows.Err()
}

// UnlockAchievement — foydalanuvchiga yutuq beradi (dublikat bo'lsa ignore)
func (q *Queries) UnlockAchievement(ctx context.Context, userID, achievementID uuid.UUID) error {
	query := `
		INSERT INTO user_achievements (id, user_id, achievement_id, unlocked_at)
		VALUES (gen_random_uuid(), $1, $2, now())
		ON CONFLICT (user_id, achievement_id) DO NOTHING`

	_, err := q.pool.Exec(ctx, query, userID, achievementID)
	return err
}

// UpsertLeaderboard — leaderboard yozuvini yaratadi yoki yangilaydi
func (q *Queries) UpsertLeaderboard(ctx context.Context, p UpsertLeaderboardParams) error {
	query := `
		INSERT INTO leaderboards (id, user_id, tag_id, period, period_key,
		                          total_games, total_correct, total_score, accuracy, updated_at)
		VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8, now())
		ON CONFLICT (user_id, tag_id, period, period_key) DO UPDATE SET
			total_games   = EXCLUDED.total_games,
			total_correct = EXCLUDED.total_correct,
			total_score   = EXCLUDED.total_score,
			accuracy      = EXCLUDED.accuracy,
			updated_at    = now()`

	_, err := q.pool.Exec(ctx, query,
		p.UserID, p.TagID, p.Period, p.PeriodKey,
		p.TotalGames, p.TotalCorrect, p.TotalScore, p.Accuracy,
	)
	return err
}

// GetLeaderboard — reyting ro'yxatini oladi
func (q *Queries) GetLeaderboard(ctx context.Context, period, periodKey string, limit int) ([]LeaderboardEntry, error) {
	query := `
		SELECT id, user_id, tag_id, period, period_key,
		       total_games, total_correct, total_score, accuracy,
		       RANK() OVER (ORDER BY total_score DESC) AS rank,
		       updated_at
		FROM leaderboards
		WHERE period = $1 AND period_key = $2 AND tag_id IS NULL
		ORDER BY total_score DESC
		LIMIT $3`

	rows, err := q.pool.Query(ctx, query, period, periodKey, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var entries []LeaderboardEntry
	for rows.Next() {
		var e LeaderboardEntry
		err := rows.Scan(
			&e.ID, &e.UserID, &e.TagID, &e.Period, &e.PeriodKey,
			&e.TotalGames, &e.TotalCorrect, &e.TotalScore, &e.Accuracy,
			&e.Rank, &e.UpdatedAt,
		)
		if err != nil {
			return nil, err
		}
		entries = append(entries, e)
	}
	return entries, rows.Err()
}

// GetUserRank — foydalanuvchining reyting o'rnini qaytaradi (rank, total, error)
func (q *Queries) GetUserRank(ctx context.Context, userID uuid.UUID, period, periodKey string) (int, int, error) {
	rankQuery := `
		SELECT rank, total
		FROM (
			SELECT user_id,
			       RANK() OVER (ORDER BY total_score DESC) AS rank,
			       COUNT(*) OVER () AS total
			FROM leaderboards
			WHERE period = $2 AND period_key = $3 AND tag_id IS NULL
		) sub
		WHERE user_id = $1`

	var rank, total int
	err := q.pool.QueryRow(ctx, rankQuery, userID, period, periodKey).Scan(&rank, &total)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return 0, 0, ErrNotFound
		}
		return 0, 0, err
	}
	return rank, total, nil
}

// GetXPLogsCountByReason — sabab bo'yicha XP log sonini oladi (achievement tekshirish uchun)
func (q *Queries) GetXPLogsCountByReason(ctx context.Context, userID uuid.UUID, reason string) (int, error) {
	var count int
	err := q.pool.QueryRow(ctx,
		`SELECT COUNT(*) FROM xp_logs WHERE user_id = $1 AND reason = $2`,
		userID, reason,
	).Scan(&count)
	return count, err
}

// GetAchievementBySlug — slug bo'yicha yutuqni oladi
func (q *Queries) GetAchievementBySlug(ctx context.Context, slug string) (*Achievement, error) {
	query := `
		SELECT id, slug, name, description, icon, xp_reward, condition_type, condition_value, created_at
		FROM achievements WHERE slug = $1`

	row := q.pool.QueryRow(ctx, query, slug)
	var a Achievement
	err := row.Scan(&a.ID, &a.Slug, &a.Name, &a.Description, &a.Icon,
		&a.XPReward, &a.ConditionType, &a.ConditionValue, &a.CreatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, err
	}
	return &a, nil
}

// HasUserAchievement — foydalanuvchida yutuq borligini tekshiradi
func (q *Queries) HasUserAchievement(ctx context.Context, userID, achievementID uuid.UUID) (bool, error) {
	var exists bool
	err := q.pool.QueryRow(ctx,
		`SELECT EXISTS(SELECT 1 FROM user_achievements WHERE user_id=$1 AND achievement_id=$2)`,
		userID, achievementID,
	).Scan(&exists)
	return exists, err
}

// GetUserWeeklyRank — foydalanuvchining haftalik reytingini oladi
func (q *Queries) GetUserWeeklyRank(ctx context.Context, userID uuid.UUID, periodKey string) (int, error) {
	rank, _, err := q.GetUserRank(ctx, userID, "weekly", periodKey)
	if err != nil {
		return 0, err
	}
	return rank, nil
}

// --- Xususiy yordamchi funksiyalar ---

type scanner interface {
	Scan(dest ...any) error
}

func scanGame(row scanner) (*Game, error) {
	var g Game
	err := row.Scan(
		&g.ID, &g.QuizID, &g.QuizSetID, &g.UserID, &g.Mode, &g.Status,
		&g.TotalQuestions, &g.CurrentQuestionIndex,
		&g.CorrectAnswers, &g.WrongAnswers, &g.SkippedAnswers,
		&g.Score, &g.TimeSpentSeconds,
		&g.IsRetry, &g.ParentGameID,
		&g.StartedAt, &g.PausedAt, &g.FinishedAt,
	)
	if err != nil {
		return nil, err
	}
	return &g, nil
}

func scanAnswer(row scanner) (*Answer, error) {
	var a Answer
	err := row.Scan(
		&a.ID, &a.GameID, &a.QuestionID, &a.UserID,
		&a.SelectedIndices, &a.IsCorrect, &a.TimeSpentMs, &a.AnsweredAt,
	)
	if err != nil {
		return nil, err
	}
	return &a, nil
}

func scanUserStats(row scanner) (*UserStats, error) {
	var s UserStats
	err := row.Scan(
		&s.ID, &s.UserID, &s.TotalXP, &s.Level,
		&s.TotalGames, &s.TotalCorrect, &s.TotalWrong, &s.Accuracy,
		&s.CurrentStreak, &s.LongestStreak,
		&s.LastPlayedAt, &s.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	return &s, nil
}

// ErrNotFound — ma'lumot topilmaganda qaytariladigan xato
var ErrNotFound = fmt.Errorf("topilmadi")

// IsoWeek — hafta kaliti (2026-W20 formatida)
func IsoWeek(t time.Time) string {
	year, week := t.ISOWeek()
	return fmt.Sprintf("%d-W%02d", year, week)
}
