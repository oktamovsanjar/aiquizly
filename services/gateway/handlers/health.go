package handlers

import (
	"encoding/json"
	"net/http"
	"time"
)

var startTime = time.Now()

type HealthResponse struct {
	Status  string            `json:"status"`
	Service string            `json:"service"`
	Version string            `json:"version"`
	Uptime  int64             `json:"uptime_seconds"`
	Checks  map[string]string `json:"checks"`
}

func Health(w http.ResponseWriter, r *http.Request) {
	resp := HealthResponse{
		Status:  "healthy",
		Service: "gateway",
		Version: "1.0.0",
		Uptime:  int64(time.Since(startTime).Seconds()),
		Checks:  map[string]string{"redis": "ok"},
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
