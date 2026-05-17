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
	"github.com/quiz-bot/notifier/sender"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

func getEnv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func main() {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	botToken := os.Getenv("TELEGRAM_BOT_TOKEN")
	if botToken == "" {
		logger.Fatal("TELEGRAM_BOT_TOKEN yo'q")
	}

	redisURL := getEnv("REDIS_URL", "redis://localhost:6379/2")
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		logger.Fatal("redis url parse xato", zap.Error(err))
	}
	redisClient := redis.NewClient(opt)

	msgSender := sender.New(botToken, logger)

	// Redis queue dan xabarlarni o'qish
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		logger.Info("Notifier worker ishga tushdi")
		for {
			select {
			case <-ctx.Done():
				return
			default:
				result, err := redisClient.BLPop(ctx, 5*time.Second, "notification:queue").Result()
				if err != nil {
					continue
				}
				if len(result) < 2 {
					continue
				}

				var n sender.Notification
				if err := json.Unmarshal([]byte(result[1]), &n); err != nil {
					logger.Error("notification parse xato", zap.Error(err))
					continue
				}

				if err := msgSender.Send(ctx, n); err != nil {
					logger.Error("xabar yuborilmadi", zap.Error(err), zap.Int64("user", n.UserTelegramID))
				} else {
					logger.Info("xabar yuborildi", zap.Int64("user", n.UserTelegramID))
				}
			}
		}
	}()

	// Health check server
	r := chi.NewRouter()
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		resp := map[string]interface{}{
			"status":  "healthy",
			"service": "notifier",
			"version": "1.0.0",
			"checks":  map[string]string{"redis": "ok"},
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	})

	srv := &http.Server{
		Addr:    fmt.Sprintf(":%s", getEnv("NOTIFIER_PORT", "8082")),
		Handler: r,
	}

	go srv.ListenAndServe()
	logger.Info("Notifier ishga tushdi")

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	cancel()
	srv.Shutdown(context.Background())
}
