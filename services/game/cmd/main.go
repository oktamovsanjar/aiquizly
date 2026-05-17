package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/signal"
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
	gameHandler := handlers.NewGameHandler(queries, lbService, logger)

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
			"db_total_conns":   stat.TotalConns(),
			"db_idle_conns":    stat.IdleConns(),
			"db_acquired_conns": stat.AcquiredConns(),
			"uptime_seconds":   int(time.Since(startTime).Seconds()),
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
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
			periodKey := r.URL.Query().Get("key")
			if periodKey == "" {
				now := time.Now()
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
			}

			top, err := queries.GetLeaderboard(r.Context(), period, periodKey, 50)
			if err != nil {
				logger.Error("leaderboard olish xatosi", zap.Error(err))
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusInternalServerError)
				json.NewEncoder(w).Encode(map[string]string{"error": "ichki xato"})
				return
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"period":     period,
				"period_key": periodKey,
				"entries":    top,
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
