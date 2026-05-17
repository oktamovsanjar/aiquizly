package handlers

import (
	"encoding/json"
	"net/http"
	"runtime"
	"sync/atomic"
	"time"
)

var (
	totalRequests  int64
	totalErrors    int64
	webhookLatency int64 // nanoseconds, last request
)

type MetricsResponse struct {
	Service        string  `json:"service"`
	TotalRequests  int64   `json:"total_requests"`
	TotalErrors    int64   `json:"total_errors"`
	UptimeSeconds  float64 `json:"uptime_seconds"`
	GoRoutines     int     `json:"goroutines"`
	MemAllocMB     float64 `json:"mem_alloc_mb"`
	LastLatencyMs  float64 `json:"last_latency_ms"`
}

func Metrics(w http.ResponseWriter, r *http.Request) {
	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)

	resp := MetricsResponse{
		Service:       "gateway",
		TotalRequests: atomic.LoadInt64(&totalRequests),
		TotalErrors:   atomic.LoadInt64(&totalErrors),
		UptimeSeconds: time.Since(startTime).Seconds(),
		GoRoutines:    runtime.NumGoroutine(),
		MemAllocMB:    float64(ms.Alloc) / 1024 / 1024,
		LastLatencyMs: float64(atomic.LoadInt64(&webhookLatency)) / 1e6,
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func IncrRequests() { atomic.AddInt64(&totalRequests, 1) }
func IncrErrors()   { atomic.AddInt64(&totalErrors, 1) }
func SetLatency(ns int64) { atomic.StoreInt64(&webhookLatency, ns) }
