// Package webui serves read-only local diagnostics to a browser.
package webui

import (
	"context"
	"embed"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"net"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
)

//go:embed static/*
var assets embed.FS

func loopbackHost(value string) bool {
	host, _, err := net.SplitHostPort(value)
	if err != nil {
		host = value
	}
	if strings.EqualFold(host, "localhost") {
		return true
	}
	ip := net.ParseIP(strings.Trim(host, "[]"))
	return ip != nil && ip.IsLoopback()
}

// Handler provides an immutable-workspace HTTP API. Requests cannot choose paths.
func Handler(root string) http.Handler {
	mux := http.NewServeMux()
	static, err := fs.Sub(assets, "static")
	if err != nil {
		panic(err)
	}
	mux.Handle("GET /assets/", http.StripPrefix("/assets/", http.FileServer(http.FS(static))))
	mux.HandleFunc("GET /api/report", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.Header().Set("Cache-Control", "no-store")
		report, err := doctor.Inspect(root)
		if err != nil {
			http.Error(w, "workspace inspection unavailable", http.StatusInternalServerError)
			return
		}
		_ = json.NewEncoder(w).Encode(report)
	})
	mux.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Header().Set("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
		data, err := assets.ReadFile("static/index.html")
		if err != nil {
			http.Error(w, "UI unavailable", http.StatusInternalServerError)
			return
		}
		_, _ = w.Write(data)
	})
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !loopbackHost(r.Host) {
			http.Error(w, "invalid Host", http.StatusForbidden)
			return
		}
		if origin := r.Header.Get("Origin"); origin != "" {
			u, err := url.Parse(origin)
			if err != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Host != r.Host || u.Path != "" || u.RawQuery != "" || u.User != nil || u.Fragment != "" {
				http.Error(w, "invalid Origin", http.StatusForbidden)
				return
			}
		}
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Referrer-Policy", "no-referrer")
		mux.ServeHTTP(w, r)
	})
}

// Serve refuses public binding, and shuts down when the CLI context is cancelled.
func Serve(ctx context.Context, root, addr string, out io.Writer) error {
	if _, err := doctor.Inspect(root); err != nil {
		return fmt.Errorf("inspect workspace: %w", err)
	}
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		return fmt.Errorf("invalid listen address: %w", err)
	}
	ip := net.ParseIP(strings.Trim(host, "[]"))
	if ip == nil || !ip.IsLoopback() {
		return errors.New("dashboard must bind to a loopback IP, e.g. 127.0.0.1:7331")
	}
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("listen: %w", err)
	}
	defer listener.Close()
	server := &http.Server{Handler: Handler(root), ReadHeaderTimeout: 5 * time.Second, IdleTimeout: 30 * time.Second}
	done := make(chan struct{})
	go func() {
		select {
		case <-ctx.Done():
			c, cancel := context.WithTimeout(context.Background(), 3*time.Second)
			defer cancel()
			_ = server.Shutdown(c)
		case <-done:
		}
	}()
	defer close(done)
	fmt.Fprintf(out, "DevPilot dashboard: http://%s/\n", listener.Addr())
	err = server.Serve(listener)
	if errors.Is(err, http.ErrServerClosed) && ctx.Err() != nil {
		return nil
	}
	return err
}
