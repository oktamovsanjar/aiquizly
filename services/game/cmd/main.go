package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/quiz-bot/game/config"
	"github.com/quiz-bot/game/db"
	"github.com/quiz-bot/game/handlers"
	"github.com/quiz-bot/game/leaderboard"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func parseTelegramID(r *http.Request) (int64, error) {
	return strconv.ParseInt(chi.URLParam(r, "telegram_id"), 10, 64)
}

func main() {
	cfg := config.Load()
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	// PostgreSQL ulanish
	pool, err := db.New(cfg.DatabaseURL)
	if err != nil {
		logger.Fatal("DB ulanish xatosi", zap.Error(err))
	}
	defer pool.Close()
	logger.Info("PostgreSQL ulanish muvaffaqiyatli")

	// Redis ulanish
	redisOpts, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		logger.Fatal("Redis URL parse xatosi", zap.Error(err))
	}
	redisClient := redis.NewClient(redisOpts)
	ctx := context.Background()
	if err := redisClient.Ping(ctx).Err(); err != nil {
		logger.Fatal("Redis ulanish xatosi", zap.Error(err))
	}
	defer redisClient.Close()
	logger.Info("Redis ulanish muvaffaqiyatli")

	// Servislar
	queries := db.NewQueries(pool)
	lbService := leaderboard.New(redisClient)
	gameHandler := handlers.NewGameHandler(queries, lbService, logger, cfg.AIEngineURL)

	// Startup: leaderboard:alltime ni DB dan tiklash (Redis restart bo'lsa)
	existing, _ := redisClient.ZCard(ctx, "leaderboard:alltime").Result()
	if existing == 0 {
		userXPs, err := queries.GetAllUserXP(ctx)
		if err != nil {
			logger.Warn("leaderboard rebuild uchun DB dan XP olishda xato", zap.Error(err))
		} else if len(userXPs) > 0 {
			entries := make([]struct {
				UserID string
				XP     float64
			}, len(userXPs))
			for i, u := range userXPs {
				entries[i] = struct {
					UserID string
					XP     float64
				}{UserID: u.UserID.String(), XP: float64(u.TotalXP)}
			}
			if err := lbService.RebuildAllTime(ctx, entries); err != nil {
				logger.Warn("leaderboard rebuild xatosi", zap.Error(err))
			} else {
				logger.Info("leaderboard:alltime DB dan tiklandi", zap.Int("users", len(entries)))
			}
		}
	}

	// Router
	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(30 * time.Second))

	// Health check
	startTime := time.Now()
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		dbStatus := "ok"
		if err := pool.Ping(r.Context()); err != nil {
			dbStatus = "error"
		}
		redisStatus := "ok"
		if err := redisClient.Ping(r.Context()).Err(); err != nil {
			redisStatus = "error"
		}
		resp := map[string]interface{}{
			"status":         "healthy",
			"service":        "game",
			"version":        "1.0.0",
			"uptime_seconds": int(time.Since(startTime).Seconds()),
			"checks": map[string]string{
				"database": dbStatus,
				"redis":    redisStatus,
			},
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	})

	// Metrics
	r.Get("/metrics", func(w http.ResponseWriter, r *http.Request) {
		stat := pool.Stat()
		resp := map[string]interface{}{
			"db_total_conns":    stat.TotalConns(),
			"db_idle_conns":     stat.IdleConns(),
			"db_acquired_conns": stat.AcquiredConns(),
			"uptime_seconds":    int(time.Since(startTime).Seconds()),
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	})

	// User stats endpointlari
	r.Route("/users/{telegram_id}", func(r chi.Router) {
		r.Get("/stats", func(w http.ResponseWriter, r *http.Request) {
			telegramID, err := parseTelegramID(r)
			if err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "telegram_id noto'g'ri"})
				return
			}
			userID, err := queries.GetUserUUIDByTelegramID(r.Context(), telegramID)
			if err != nil {
				writeJSON(w, http.StatusOK, map[string]interface{}{
					"total_xp": 0, "level": "beginner", "total_games": 0,
					"total_correct": 0, "total_wrong": 0, "accuracy": 0.0,
					"current_streak": 0, "longest_streak": 0,
				})
				return
			}
			stats, err := queries.GetUserStats(r.Context(), userID)
			if err != nil {
				writeJSON(w, http.StatusOK, map[string]interface{}{
					"total_xp": 0, "level": "beginner", "total_games": 0,
					"total_correct": 0, "total_wrong": 0, "accuracy": 0.0,
					"current_streak": 0, "longest_streak": 0,
				})
				return
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(stats)
		})

		r.Get("/rank", func(w http.ResponseWriter, r *http.Request) {
			telegramID, err := parseTelegramID(r)
			if err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "telegram_id noto'g'ri"})
				return
			}
			userID, err := queries.GetUserUUIDByTelegramID(r.Context(), telegramID)
			if err != nil {
				writeJSON(w, http.StatusOK, map[string]interface{}{"rank": 0, "total": 0})
				return
			}
			period := r.URL.Query().Get("period")
			if period == "" {
				period = "all"
			}
			now := time.Now()
			var periodKey string
			switch period {
			case "daily":
				periodKey = now.Format("2006-01-02")
			case "weekly":
				year, week := now.ISOWeek()
				periodKey = fmt.Sprintf("%d-W%02d", year, week)
			case "monthly":
				periodKey = now.Format("2006-01")
			default:
				periodKey = "alltime"
			}
			rank, score, err := lbService.GetUserRank(r.Context(), period, periodKey, userID.String())
			if err != nil {
				writeJSON(w, http.StatusOK, map[string]interface{}{"rank": 0, "total": 0})
				return
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{"rank": rank, "total": int(score)})
		})

		r.Get("/achievements", func(w http.ResponseWriter, r *http.Request) {
			telegramID, err := parseTelegramID(r)
			if err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "telegram_id noto'g'ri"})
				return
			}
			all, err := queries.GetAchievements(r.Context())
			if err != nil {
				logger.Error("achievements olish xatosi", zap.Error(err))
				writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "ichki xato"})
				return
			}
			userID, uerr := queries.GetUserUUIDByTelegramID(r.Context(), telegramID)
			unlocked := []map[string]interface{}{}
			locked := []map[string]interface{}{}
			unlockedIDs := map[string]bool{}
			if uerr == nil {
				userAchs, _ := queries.GetUserAchievements(r.Context(), userID)
				for _, ua := range userAchs {
					if ua.Achievement != nil {
						unlocked = append(unlocked, map[string]interface{}{
							"slug":        ua.Achievement.Slug,
							"name":        ua.Achievement.Name,
							"description": ua.Achievement.Description,
							"icon":        ua.Achievement.Icon,
							"xp_reward":   ua.Achievement.XPReward,
							"unlocked_at": ua.UnlockedAt,
						})
						unlockedIDs[ua.AchievementID.String()] = true
					}
				}
			}
			for _, a := range all {
				if !unlockedIDs[a.ID.String()] {
					locked = append(locked, map[string]interface{}{
						"slug":        a.Slug,
						"name":        a.Name,
						"description": a.Description,
						"icon":        a.Icon,
						"xp_reward":   a.XPReward,
					})
				}
			}
			writeJSON(w, http.StatusOK, map[string]interface{}{
				"unlocked": unlocked,
				"locked":   locked,
				"total":    len(all),
			})
		})

		r.Post("/xp", func(w http.ResponseWriter, r *http.Request) {
			telegramID, err := parseTelegramID(r)
			if err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "telegram_id noto'g'ri"})
				return
			}
			userID, err := queries.GetUserUUIDByTelegramID(r.Context(), telegramID)
			if err != nil {
				writeJSON(w, http.StatusNotFound, map[string]string{"error": "foydalanuvchi topilmadi"})
				return
			}
			var body struct {
				XP     int    `json:"xp"`
				Reason string `json:"reason"`
			}
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "so'rov noto'g'ri"})
				return
			}
			if err := queries.AddXPLog(r.Context(), db.AddXPLogParams{
				UserID: userID, Amount: body.XP, Reason: body.Reason,
			}); err != nil {
				logger.Error("xp log xatosi", zap.Error(err))
				writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "ichki xato"})
				return
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{"ok": true, "xp": body.XP})
		})
	})

	// Game endpointlari
	r.Route("/games", func(r chi.Router) {
		r.Post("/", gameHandler.CreateGame)
		r.Get("/{game_id}", gameHandler.GetGame)
		r.Put("/{game_id}/answer", gameHandler.SubmitAnswer)
		r.Put("/{game_id}/pause", gameHandler.PauseGame)
		r.Put("/{game_id}/resume", gameHandler.ResumeGame)
		r.Put("/{game_id}/stop", gameHandler.StopGame)
		r.Put("/{game_id}/finish", gameHandler.FinishGame)
		r.Get("/{game_id}/wrong", gameHandler.GetWrongAnswers)
	})

	// Leaderboard endpointlari
	r.Route("/leaderboard", func(r chi.Router) {
		r.Get("/{period}", func(w http.ResponseWriter, r *http.Request) {
			period := chi.URLParam(r, "period")
			now := time.Now()
			var periodKey string
			switch period {
			case "daily":
				periodKey = now.Format("2006-01-02")
			case "weekly":
				year, week := now.ISOWeek()
				periodKey = fmt.Sprintf("%d-W%02d", year, week)
			case "monthly":
				periodKey = now.Format("2006-01")
			default:
				period = "all"
				periodKey = "alltime"
			}

			limitStr := r.URL.Query().Get("limit")
			limit := 50
			if limitStr != "" {
				if n, err := strconv.Atoi(limitStr); err == nil && n > 0 {
					limit = n
				}
			}

			entries, err := lbService.GetTopN(r.Context(), period, periodKey, limit)
			if err != nil {
				logger.Error("leaderboard olish xatosi", zap.Error(err))
				writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "ichki xato"})
				return
			}
			writeJSON(w, http.StatusOK, map[string]interface{}{
				"period":     period,
				"period_key": periodKey,
				"entries":    entries,
			})
		})
	})

	// Server
	srv := &http.Server{
		Addr:         fmt.Sprintf(":%s", cfg.Port),
		Handler:      r,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		logger.Info("Game xizmati ishga tushdi", zap.String("port", cfg.Port))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("server xatosi", zap.Error(err))
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Game xizmati to'xtatilmoqda...")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	srv.Shutdown(shutdownCtx)
	logger.Info("Game xizmati to'xtatildi")
}
