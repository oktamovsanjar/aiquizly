package router

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	chimiddleware "github.com/go-chi/chi/v5/middleware"
	"github.com/quiz-bot/gateway/handlers"
	gw "github.com/quiz-bot/gateway/middleware"
	"go.uber.org/zap"
)

func New(botServiceURL, botToken string, logger *zap.Logger) http.Handler {
	r := chi.NewRouter()

	r.Use(chimiddleware.RequestID)
	r.Use(chimiddleware.RealIP)
	r.Use(chimiddleware.Recoverer)
	r.Use(gw.RateLimit)
	r.Use(gw.Logger(logger))

	webhookHandler := handlers.NewWebhookHandler(botServiceURL, botToken, logger)

	r.Get("/health", handlers.Health)
	r.Get("/metrics", handlers.Metrics)
	r.Post("/webhook", webhookHandler.Handle)

	return r
}
