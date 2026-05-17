package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/quiz-bot/game/achievement"
	"github.com/quiz-bot/game/db"
	"github.com/quiz-bot/game/scoring"
	"github.com/quiz-bot/game/streak"
	"go.uber.org/zap"
)

// GameHandler — game HTTP handlerlari
type GameHandler struct {
	queries *db.Queries
	lb      LeaderboardUpdater
	log     *zap.Logger
}

// LeaderboardUpdater — leaderboard yangilash interfeysi
type LeaderboardUpdater interface {
	UpdateAll(ctx context.Context, userID uuid.UUID, score int, correct int, games int, accuracy float64) error
}

// NewGameHandler — GameHandler yaratadi
func NewGameHandler(queries *db.Queries, lb LeaderboardUpdater, log *zap.Logger) *GameHandler {
	return &GameHandler{queries: queries, lb: lb, log: log}
}

// --- POST /games ---

type createGameRequest struct {
	QuizID         string `json:"quiz_id"`
	QuizSetID      string `json:"quiz_set_id"`
	UserID         string `json:"user_id"`
	Mode           string `json:"mode"`
	TotalQuestions int    `json:"total_questions"`
}

type createGameResponse struct {
	GameID string `json:"game_id"`
	Status string `json:"status"`
}

func (h *GameHandler) CreateGame(w http.ResponseWriter, r *http.Request) {
	var req createGameRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "so'rov tanasi noto'g'ri")
		return
	}

	quizID, err := uuid.Parse(req.QuizID)
	if err != nil {
		writeError(w, http.StatusBadRequest, "quiz_id noto'g'ri")
		return
	}
	quizSetID, err := uuid.Parse(req.QuizSetID)
	if err != nil {
		writeError(w, http.StatusBadRequest, "quiz_set_id noto'g'ri")
		return
	}
	userID, err := uuid.Parse(req.UserID)
	if err != nil {
		writeError(w, http.StatusBadRequest, "user_id noto'g'ri")
		return
	}

	if req.TotalQuestions <= 0 {
		writeError(w, http.StatusBadRequest, "total_questions 0 dan katta bo'lishi kerak")
		return
	}

	mode := req.Mode
	if mode == "" {
		mode = "solo"
	}

	game, err := h.queries.CreateGame(r.Context(), db.CreateGameParams{
		QuizID:         quizID,
		QuizSetID:      quizSetID,
		UserID:         userID,
		Mode:           mode,
		TotalQuestions: req.TotalQuestions,
	})
	if err != nil {
		h.log.Error("game yaratish xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "game yaratib bo'lmadi")
		return
	}

	writeJSON(w, http.StatusCreated, createGameResponse{
		GameID: game.ID.String(),
		Status: game.Status,
	})
}

// --- GET /games/{game_id} ---

func (h *GameHandler) GetGame(w http.ResponseWriter, r *http.Request) {
	gameID, err := parseGameID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "game_id noto'g'ri")
		return
	}

	game, err := h.queries.GetGame(r.Context(), gameID)
	if err != nil {
		if errors.Is(err, db.ErrNotFound) {
			writeError(w, http.StatusNotFound, "game topilmadi")
			return
		}
		h.log.Error("game olish xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "ichki xato")
		return
	}

	writeJSON(w, http.StatusOK, game)
}

// --- PUT /games/{game_id}/answer ---

type answerRequest struct {
	QuestionID      string `json:"question_id"`
	SelectedIndices []int  `json:"selected_indices"`
	TimeSpentMs     int    `json:"time_spent_ms"`
}

type answerResponse struct {
	IsCorrect      bool   `json:"is_correct"`
	CorrectIndices []int  `json:"correct_indices"`
	Explanation    string `json:"explanation"`
	Score          int    `json:"score"`
}

func (h *GameHandler) SubmitAnswer(w http.ResponseWriter, r *http.Request) {
	gameID, err := parseGameID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "game_id noto'g'ri")
		return
	}

	var req answerRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "so'rov tanasi noto'g'ri")
		return
	}

	questionID, err := uuid.Parse(req.QuestionID)
	if err != nil {
		writeError(w, http.StatusBadRequest, "question_id noto'g'ri")
		return
	}

	game, err := h.queries.GetGame(r.Context(), gameID)
	if err != nil {
		if errors.Is(err, db.ErrNotFound) {
			writeError(w, http.StatusNotFound, "game topilmadi")
			return
		}
		h.log.Error("game olish xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "ichki xato")
		return
	}

	if game.Status != "active" {
		writeError(w, http.StatusConflict, "game faol emas")
		return
	}

	// Savol ma'lumotlarini olish uchun questions jadvaliga murojaat (read-only)
	// Game xizmati faqat o'z jadvallariga yozadi, lekin questions jadvalidan o'qishi mumkin
	var correctIndices []int
	var explanation string
	var isCorrect bool

	row := h.queries.Pool().QueryRow(r.Context(),
		`SELECT correct_indices, explanation FROM questions WHERE id = $1`,
		questionID,
	)
	err = row.Scan(&correctIndices, &explanation)
	if err != nil {
		h.log.Error("savol ma'lumotlarini olish xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "savol topilmadi")
		return
	}

	// To'g'rilikni tekshirish
	isCorrect = indicesMatch(req.SelectedIndices, correctIndices)

	isCorrectPtr := &isCorrect
	if len(req.SelectedIndices) == 0 {
		isCorrectPtr = nil // skip
	}

	if err := h.queries.SaveAnswer(r.Context(), db.SaveAnswerParams{
		GameID:          gameID,
		QuestionID:      questionID,
		UserID:          game.UserID,
		SelectedIndices: req.SelectedIndices,
		IsCorrect:       isCorrectPtr,
		TimeSpentMs:     req.TimeSpentMs,
	}); err != nil {
		h.log.Error("javob saqlash xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "javobni saqlab bo'lmadi")
		return
	}

	// Game statistikasini yangilash
	newCorrect := game.CorrectAnswers
	newWrong := game.WrongAnswers
	newSkipped := game.SkippedAnswers

	if isCorrectPtr == nil {
		newSkipped++
	} else if isCorrect {
		newCorrect++
	} else {
		newWrong++
	}

	newIdx := game.CurrentQuestionIndex + 1
	newTimeSpent := game.TimeSpentSeconds + req.TimeSpentMs/1000

	totalAnswered := newCorrect + newWrong
	currentScore := 0
	if totalAnswered > 0 {
		currentScore = scoring.CalculateScore(newCorrect, game.TotalQuestions,
			int64(newTimeSpent*1000), int64(game.TotalQuestions*30000))
	}

	updateParams := db.UpdateGameParams{
		Status:               game.Status,
		CurrentQuestionIndex: newIdx,
		CorrectAnswers:       newCorrect,
		WrongAnswers:         newWrong,
		SkippedAnswers:       newSkipped,
		Score:                currentScore,
		TimeSpentSeconds:     newTimeSpent,
		PausedAt:             game.PausedAt,
		FinishedAt:           game.FinishedAt,
	}
	if err := h.queries.UpdateGame(r.Context(), gameID, updateParams); err != nil {
		h.log.Error("game yangilash xatosi", zap.Error(err))
	}

	resp := answerResponse{
		IsCorrect:      isCorrect,
		CorrectIndices: correctIndices,
		Explanation:    explanation,
		Score:          currentScore,
	}
	writeJSON(w, http.StatusOK, resp)
}

// --- PUT /games/{game_id}/pause ---

func (h *GameHandler) PauseGame(w http.ResponseWriter, r *http.Request) {
	gameID, err := parseGameID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "game_id noto'g'ri")
		return
	}

	game, err := h.queries.GetGame(r.Context(), gameID)
	if err != nil {
		if errors.Is(err, db.ErrNotFound) {
			writeError(w, http.StatusNotFound, "game topilmadi")
			return
		}
		writeError(w, http.StatusInternalServerError, "ichki xato")
		return
	}

	if game.Status != "active" {
		writeError(w, http.StatusConflict, "game faol emas, pauza qilib bo'lmaydi")
		return
	}

	now := time.Now()
	if err := h.queries.UpdateGame(r.Context(), gameID, db.UpdateGameParams{
		Status:               "paused",
		CurrentQuestionIndex: game.CurrentQuestionIndex,
		CorrectAnswers:       game.CorrectAnswers,
		WrongAnswers:         game.WrongAnswers,
		SkippedAnswers:       game.SkippedAnswers,
		Score:                game.Score,
		TimeSpentSeconds:     game.TimeSpentSeconds,
		PausedAt:             &now,
		FinishedAt:           game.FinishedAt,
	}); err != nil {
		h.log.Error("game pauza xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "pauza qilib bo'lmadi")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "paused"})
}

// --- PUT /games/{game_id}/resume ---

func (h *GameHandler) ResumeGame(w http.ResponseWriter, r *http.Request) {
	gameID, err := parseGameID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "game_id noto'g'ri")
		return
	}

	game, err := h.queries.GetGame(r.Context(), gameID)
	if err != nil {
		if errors.Is(err, db.ErrNotFound) {
			writeError(w, http.StatusNotFound, "game topilmadi")
			return
		}
		writeError(w, http.StatusInternalServerError, "ichki xato")
		return
	}

	if game.Status != "paused" {
		writeError(w, http.StatusConflict, "game pauza holatida emas")
		return
	}

	if err := h.queries.UpdateGame(r.Context(), gameID, db.UpdateGameParams{
		Status:               "active",
		CurrentQuestionIndex: game.CurrentQuestionIndex,
		CorrectAnswers:       game.CorrectAnswers,
		WrongAnswers:         game.WrongAnswers,
		SkippedAnswers:       game.SkippedAnswers,
		Score:                game.Score,
		TimeSpentSeconds:     game.TimeSpentSeconds,
		PausedAt:             nil,
		FinishedAt:           game.FinishedAt,
	}); err != nil {
		h.log.Error("game davom ettirish xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "davom ettirb bo'lmadi")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "active"})
}

// --- PUT /games/{game_id}/stop ---

func (h *GameHandler) StopGame(w http.ResponseWriter, r *http.Request) {
	gameID, err := parseGameID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "game_id noto'g'ri")
		return
	}

	game, err := h.queries.GetGame(r.Context(), gameID)
	if err != nil {
		if errors.Is(err, db.ErrNotFound) {
			writeError(w, http.StatusNotFound, "game topilmadi")
			return
		}
		writeError(w, http.StatusInternalServerError, "ichki xato")
		return
	}

	if game.Status == "completed" || game.Status == "stopped" {
		writeError(w, http.StatusConflict, "game allaqachon tugagan")
		return
	}

	now := time.Now()
	if err := h.queries.UpdateGame(r.Context(), gameID, db.UpdateGameParams{
		Status:               "stopped",
		CurrentQuestionIndex: game.CurrentQuestionIndex,
		CorrectAnswers:       game.CorrectAnswers,
		WrongAnswers:         game.WrongAnswers,
		SkippedAnswers:       game.SkippedAnswers,
		Score:                game.Score,
		TimeSpentSeconds:     game.TimeSpentSeconds,
		PausedAt:             game.PausedAt,
		FinishedAt:           &now,
	}); err != nil {
		h.log.Error("game to'xtatish xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "to'xtatib bo'lmadi")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "stopped"})
}

// --- PUT /games/{game_id}/finish ---

type finishGameResponse struct {
	Score           int      `json:"score"`
	Correct         int      `json:"correct"`
	Wrong           int      `json:"wrong"`
	Skipped         int      `json:"skipped"`
	XPEarned        int      `json:"xp_earned"`
	NewAchievements []string `json:"new_achievements"`
}

func (h *GameHandler) FinishGame(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	gameID, err := parseGameID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "game_id noto'g'ri")
		return
	}

	game, err := h.queries.GetGame(ctx, gameID)
	if err != nil {
		if errors.Is(err, db.ErrNotFound) {
			writeError(w, http.StatusNotFound, "game topilmadi")
			return
		}
		h.log.Error("game olish xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "ichki xato")
		return
	}

	if game.Status == "completed" {
		writeError(w, http.StatusConflict, "game allaqachon tugatilgan")
		return
	}

	// Yakuniy ball hisoblash
	finalScore := scoring.CalculateScore(
		game.CorrectAnswers, game.TotalQuestions,
		int64(game.TimeSpentSeconds*1000),
		int64(game.TotalQuestions*30000),
	)

	now := time.Now()
	if err := h.queries.UpdateGame(ctx, gameID, db.UpdateGameParams{
		Status:               "completed",
		CurrentQuestionIndex: game.CurrentQuestionIndex,
		CorrectAnswers:       game.CorrectAnswers,
		WrongAnswers:         game.WrongAnswers,
		SkippedAnswers:       game.SkippedAnswers,
		Score:                finalScore,
		TimeSpentSeconds:     game.TimeSpentSeconds,
		PausedAt:             game.PausedAt,
		FinishedAt:           &now,
	}); err != nil {
		h.log.Error("game tugatish xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "tugatib bo'lmadi")
		return
	}

	// Streak yangilash
	newStreak, err := streak.UpdateStreak(ctx, h.queries.Pool(), game.UserID)
	if err != nil {
		h.log.Error("streak yangilash xatosi", zap.Error(err), zap.String("user_id", game.UserID.String()))
		newStreak = 0
	}

	// XP hisoblash
	xpEarned := scoring.CalculateXP(game.CorrectAnswers, game.TotalQuestions, newStreak)

	// Streak milestone bonusi
	streakBonus := streak.ShouldAwardStreakBonus(newStreak)
	xpEarned += streakBonus

	// UserStats olish va yangilash
	stats, err := h.queries.GetUserStats(ctx, game.UserID)
	if err != nil && !errors.Is(err, db.ErrNotFound) {
		h.log.Error("user stats olish xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "statistika xatosi")
		return
	}

	var (
		totalXP      int
		totalGames   int
		totalCorrect int
		totalWrong   int
		longestStreak int
	)

	if stats != nil {
		totalXP = stats.TotalXP
		totalGames = stats.TotalGames
		totalCorrect = stats.TotalCorrect
		totalWrong = stats.TotalWrong
		longestStreak = stats.LongestStreak
	}

	totalXP += xpEarned
	totalGames++
	totalCorrect += game.CorrectAnswers
	totalWrong += game.WrongAnswers

	newLevel := scoring.DetermineLevel(totalXP)

	var accuracy float64
	if totalCorrect+totalWrong > 0 {
		accuracy = float64(totalCorrect) / float64(totalCorrect+totalWrong) * 100
	}

	if newStreak > longestStreak {
		longestStreak = newStreak
	}

	lastPlayed := now
	upsertParams := db.UpsertUserStatsParams{
		UserID:        game.UserID,
		TotalXP:       totalXP,
		Level:         newLevel,
		TotalGames:    totalGames,
		TotalCorrect:  totalCorrect,
		TotalWrong:    totalWrong,
		Accuracy:      accuracy,
		CurrentStreak: newStreak,
		LongestStreak: longestStreak,
		LastPlayedAt:  &lastPlayed,
	}
	if err := h.queries.UpsertUserStats(ctx, upsertParams); err != nil {
		h.log.Error("user stats yangilash xatosi", zap.Error(err))
	}

	// XP log yozish
	gameRef := game.ID
	xpLogs := []db.AddXPLogParams{
		{UserID: game.UserID, Amount: scoring.BaseXP, Reason: "quiz_complete", ReferenceID: &gameRef},
	}
	if game.CorrectAnswers == game.TotalQuestions {
		xpLogs = append(xpLogs, db.AddXPLogParams{
			UserID: game.UserID, Amount: scoring.PerfectBonusXP,
			Reason: "perfect_score", ReferenceID: &gameRef,
		})
	}
	if newStreak > 0 {
		streakXP := newStreak * scoring.StreakXPPerDay
		if streakBonus > 0 {
			streakXP += streakBonus
		}
		xpLogs = append(xpLogs, db.AddXPLogParams{
			UserID: game.UserID, Amount: streakXP,
			Reason: "streak", ReferenceID: &gameRef,
		})
	}
	for _, lp := range xpLogs {
		if err := h.queries.AddXPLog(ctx, lp); err != nil {
			h.log.Error("xp log yozish xatosi", zap.Error(err))
		}
	}

	// Achievement tekshirish
	updatedStats := &db.UserStats{
		UserID:        game.UserID,
		TotalXP:       totalXP,
		Level:         newLevel,
		TotalGames:    totalGames,
		TotalCorrect:  totalCorrect,
		TotalWrong:    totalWrong,
		Accuracy:      accuracy,
		CurrentStreak: newStreak,
		LongestStreak: longestStreak,
	}

	event := "game_complete"
	if game.CorrectAnswers == game.TotalQuestions {
		event = "perfect_score"
	}

	newAchievements, err := achievement.Check(ctx, h.queries.Pool(), game.UserID, updatedStats, event)
	if err != nil {
		h.log.Error("achievement tekshirish xatosi", zap.Error(err))
	}

	// Achievement XP larini ham qo'shish
	for _, ach := range newAchievements {
		if ach.XPReward > 0 {
			if err := h.queries.AddXPLog(ctx, db.AddXPLogParams{
				UserID: game.UserID, Amount: ach.XPReward,
				Reason: "achievement",
			}); err != nil {
				h.log.Error("achievement xp log xatosi", zap.Error(err))
			}
			xpEarned += ach.XPReward
		}
	}

	achSlugs := make([]string, len(newAchievements))
	for i, a := range newAchievements {
		achSlugs[i] = a.AchievementSlug
	}

	writeJSON(w, http.StatusOK, finishGameResponse{
		Score:           finalScore,
		Correct:         game.CorrectAnswers,
		Wrong:           game.WrongAnswers,
		Skipped:         game.SkippedAnswers,
		XPEarned:        xpEarned,
		NewAchievements: achSlugs,
	})
}

// --- GET /games/{game_id}/wrong ---

func (h *GameHandler) GetWrongAnswers(w http.ResponseWriter, r *http.Request) {
	gameID, err := parseGameID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "game_id noto'g'ri")
		return
	}

	answers, err := h.queries.GetWrongAnswers(r.Context(), gameID)
	if err != nil {
		h.log.Error("noto'g'ri javoblarni olish xatosi", zap.Error(err))
		writeError(w, http.StatusInternalServerError, "ichki xato")
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"game_id": gameID,
		"answers": answers,
		"count":   len(answers),
	})
}

// --- Yordamchi funksiyalar ---

func parseGameID(r *http.Request) (uuid.UUID, error) {
	return uuid.Parse(chi.URLParam(r, "game_id"))
}

func indicesMatch(selected, correct []int) bool {
	if len(selected) != len(correct) {
		return false
	}
	m := make(map[int]bool, len(correct))
	for _, v := range correct {
		m[v] = true
	}
	for _, v := range selected {
		if !m[v] {
			return false
		}
	}
	return true
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
