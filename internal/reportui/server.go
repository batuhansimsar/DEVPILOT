// Package reportui serves a read-only loopback dashboard for DevPilot's doctor.
package reportui

import (
	"embed"
	"encoding/json"
	"io/fs"
	"net/http"
	"strings"
)

// Inspector is a read-only source of doctor reports. Keeping it injected makes
// the web handler testable without running repository code or network services.
type Inspector func(projectPath string) (any, error)

//go:embed assets/*
var static embed.FS

func Handler(path string, inspect Inspector) http.Handler {
	sub, _ := fs.Sub(static, "assets")
	mux := http.NewServeMux()
	mux.HandleFunc("/api/doctor", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.Header().Set("Cache-Control", "no-store")
		report, err := inspect(path)
		if err != nil {
			http.Error(w, "Doctor inspection failed", http.StatusInternalServerError)
			return
		}
		if err := json.NewEncoder(w).Encode(report); err != nil {
			return
		}
	})
	mux.Handle("/", http.FileServer(http.FS(sub)))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Referrer-Policy", "no-referrer")
		w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
		if !loopbackHost(r.Host) {
			http.Error(w, "Untrusted Host header", http.StatusForbidden)
			return
		}
		mux.ServeHTTP(w, r)
	})
}
func loopbackHost(raw string) bool {
	host := raw
	if strings.HasPrefix(host, "[") {
		end := strings.IndexByte(host, ']')
		if end < 0 {
			return false
		}
		host = host[1:end]
	} else if at := strings.IndexByte(host, ':'); at >= 0 {
		host = host[:at]
	}
	return host == "localhost" || host == "127.0.0.1" || host == "::1"
}
