package sender

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"go.uber.org/zap"
)

const telegramAPIBase = "https://api.telegram.org/bot"

// Notification — Redis queue dan keladigan xabar formati
type Notification struct {
	UserTelegramID int64             `json:"user_telegram_id"`
	Text           string            `json:"text"`
	ParseMode      string            `json:"parse_mode,omitempty"` // HTML | Markdown
	TemplateSlug   string            `json:"template_slug,omitempty"`
	TemplateVars   map[string]string `json:"template_vars,omitempty"`
	ReferenceType  string            `json:"reference_type,omitempty"`
	ReferenceID    string            `json:"reference_id,omitempty"`
	InlineButtons  []InlineButton    `json:"inline_buttons,omitempty"`
}

type InlineButton struct {
	Text         string `json:"text"`
	CallbackData string `json:"callback_data,omitempty"`
	URL          string `json:"url,omitempty"`
}

type sendMessageRequest struct {
	ChatID      int64         `json:"chat_id"`
	Text        string        `json:"text"`
	ParseMode   string        `json:"parse_mode,omitempty"`
	ReplyMarkup *inlineMarkup `json:"reply_markup,omitempty"`
}

type inlineMarkup struct {
	InlineKeyboard [][]inlineButton `json:"inline_keyboard"`
}

type inlineButton struct {
	Text         string `json:"text"`
	CallbackData string `json:"callback_data,omitempty"`
	URL          string `json:"url,omitempty"`
}

type Sender struct {
	botToken   string
	httpClient *http.Client
	logger     *zap.Logger
}

func New(botToken string, logger *zap.Logger) *Sender {
	return &Sender{
		botToken: botToken,
		httpClient: &http.Client{
			Timeout: 15 * time.Second,
		},
		logger: logger,
	}
}

// Send — bitta notification ni Telegram ga yuboradi, 3 marta retry bilan
func (s *Sender) Send(ctx context.Context, n Notification) error {
	text := n.Text
	if text == "" && n.TemplateSlug != "" {
		text = renderTemplate(n.TemplateSlug, n.TemplateVars)
	}
	if text == "" {
		return fmt.Errorf("xabar matni bo'sh")
	}

	req := sendMessageRequest{
		ChatID:    n.UserTelegramID,
		Text:      text,
		ParseMode: n.ParseMode,
	}
	if len(n.InlineButtons) > 0 {
		row := make([]inlineButton, 0, len(n.InlineButtons))
		for _, b := range n.InlineButtons {
			row = append(row, inlineButton{
				Text:         b.Text,
				CallbackData: b.CallbackData,
				URL:          b.URL,
			})
		}
		req.ReplyMarkup = &inlineMarkup{InlineKeyboard: [][]inlineButton{row}}
	}

	var lastErr error
	for attempt := 0; attempt < 3; attempt++ {
		if attempt > 0 {
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(time.Duration(attempt*2) * time.Second):
			}
		}

		if err := s.doSend(ctx, req); err != nil {
			lastErr = err
			s.logger.Warn("yuborish xatosi, qayta urinish",
				zap.Int("attempt", attempt+1),
				zap.Error(err),
				zap.Int64("user", n.UserTelegramID),
			)
			continue
		}
		return nil
	}
	return fmt.Errorf("3 urinishdan keyin ham yuborilmadi: %w", lastErr)
}

// SendBatch — ko'p notification ni parallel yuboradi (max 30 goroutine)
func (s *Sender) SendBatch(ctx context.Context, notifications []Notification) []error {
	type result struct {
		idx int
		err error
	}

	sem := make(chan struct{}, 30)
	results := make(chan result, len(notifications))

	for i, n := range notifications {
		sem <- struct{}{}
		go func(idx int, notif Notification) {
			defer func() { <-sem }()
			err := s.Send(ctx, notif)
			results <- result{idx: idx, err: err}
		}(i, n)
	}

	errs := make([]error, len(notifications))
	for range notifications {
		r := <-results
		errs[r.idx] = r.err
	}
	return errs
}

// renderTemplate — template_slug bo'yicha shablon matnini qaytaradi va {var} placeholder larni almashtiradi
func renderTemplate(slug string, vars map[string]string) string {
	templates := map[string]string{
		"quiz_ready":          "✅ \"{title}\" tayyor!\n{total_questions} savol → {set_count} set",
		"daily_reminder":      "🔥 {streak} kunlik streak!\nBugun ham davom ettiring.\n👉 /quiz",
		"new_quiz_in_group":   "📌 {group_name} — yangi quiz!\n📋 \"{quiz_title}\"\n{total_questions} savol | {set_count} set",
		"achievement_unlock":  "🏅 Yangi yutuq: \"{achievement_name}\"!\n+{xp_reward} XP qo'shildi",
		"referral_joined":     "👥 Do'stingiz @{username} ro'yxatdan o'tdi!\n+50 XP va +3 kun premium qo'shildi",
		"streak_broken":       "😔 Streak uzildi ({streak} kun edi)\nQaytadan boshlang!\n👉 /quiz",
		"subscription_expiry": "💎 Obunangiz {days} kun ichida tugaydi.\nYangilash: /premium",
	}

	text, ok := templates[slug]
	if !ok {
		return ""
	}

	for key, val := range vars {
		text = strings.ReplaceAll(text, "{"+key+"}", val)
	}
	return text
}

func (s *Sender) doSend(ctx context.Context, req sendMessageRequest) error {
	body, err := json.Marshal(req)
	if err != nil {
		return fmt.Errorf("json marshal: %w", err)
	}

	url := fmt.Sprintf("%s%s/sendMessage", telegramAPIBase, s.botToken)
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("request yaratish: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := s.httpClient.Do(httpReq)
	if err != nil {
		return fmt.Errorf("telegram api: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusTooManyRequests {
		return fmt.Errorf("rate limit (429)")
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("telegram api status: %d", resp.StatusCode)
	}
	return nil
}
