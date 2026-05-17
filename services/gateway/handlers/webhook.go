package handlers

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"io"
	"net/http"
	"time"

	"go.uber.org/zap"
)

type WebhookHandler struct {
	botServiceURL string
	botToken      string
	logger        *zap.Logger
	httpClient    *http.Client
}

func NewWebhookHandler(botServiceURL, botToken string, logger *zap.Logger) *WebhookHandler {
	return &WebhookHandler{
		botServiceURL: botServiceURL,
		botToken:      botToken,
		logger:        logger,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Handle — Telegram webhookni qabul qilib bot servisga proxy qiladi
func (h *WebhookHandler) Handle(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	IncrRequests()

	body, err := io.ReadAll(io.LimitReader(r.Body, 10*1024*1024)) // 10MB limit
	if err != nil {
		h.logger.Error("request body o'qilmadi", zap.Error(err))
		IncrErrors()
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	// Telegram webhook signature tekshirish (ixtiyoriy, agar secret token sozlangan bo'lsa)
	if h.botToken != "" {
		secretToken := r.Header.Get("X-Telegram-Bot-Api-Secret-Token")
		if secretToken != "" && !h.verifySecret(secretToken, body) {
			h.logger.Warn("noto'g'ri webhook signature")
			IncrErrors()
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
	}

	targetURL := h.botServiceURL + "/webhook"
	req, err := http.NewRequestWithContext(r.Context(), http.MethodPost, targetURL, bytes.NewReader(body))
	if err != nil {
		h.logger.Error("request yaratilmadi", zap.Error(err))
		IncrErrors()
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	req.Header.Set("Content-Type", "application/json")

	// Request ID forwarding
	if rid := r.Header.Get("X-Request-ID"); rid != "" {
		req.Header.Set("X-Request-ID", rid)
	}

	resp, err := h.httpClient.Do(req)
	if err != nil {
		h.logger.Error("bot servisga ulanmadi", zap.Error(err))
		IncrErrors()
		http.Error(w, "service unavailable", http.StatusServiceUnavailable)
		return
	}
	defer resp.Body.Close()

	latency := time.Since(start).Nanoseconds()
	SetLatency(latency)

	h.logger.Info("webhook proxied",
		zap.Int("status", resp.StatusCode),
		zap.Int64("latency_ms", latency/1e6),
	)

	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

func (h *WebhookHandler) verifySecret(provided string, body []byte) bool {
	mac := hmac.New(sha256.New, []byte(h.botToken))
	mac.Write(body)
	expected := hex.EncodeToString(mac.Sum(nil))
	return hmac.Equal([]byte(provided), []byte(expected))
}
