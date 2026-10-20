package webui

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func request(t *testing.T, h http.Handler, method, path, host, origin string) *httptest.ResponseRecorder {
	t.Helper()
	r := httptest.NewRequest(method, path, nil)
	r.Host = host
	if origin != "" {
		r.Header.Set("Origin", origin)
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}
func TestDashboardAndReport(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.org/demo\n\ngo 1.23\n"), 0600); err != nil {
		t.Fatal(err)
	}
	h := Handler(root)
	page := request(t, h, "GET", "/", "127.0.0.1:7331", "")
	if page.Code != 200 || !strings.Contains(page.Body.String(), "DevPilot") {
		t.Fatalf("page: %d", page.Code)
	}
	if strings.Contains(page.Header().Get("Content-Security-Policy"), "unsafe-inline") {
		t.Fatal("weak CSP")
	}
	api := request(t, h, "GET", "/api/report", "127.0.0.1:7331", "")
	var report map[string]any
	if api.Code != 200 || json.Unmarshal(api.Body.Bytes(), &report) != nil {
		t.Fatalf("invalid API: %d %s", api.Code, api.Body.String())
	}
	if report["path"] != root {
		t.Fatalf("wrong inspected path: %v", report["path"])
	}
	script := request(t, h, "GET", "/assets/app.js", "127.0.0.1:7331", "")
	if script.Code != 200 || !strings.Contains(script.Body.String(), "refresh()") {
		t.Fatal("JS asset unavailable")
	}
}
func TestRejectUntrustedHostsAndMethods(t *testing.T) {
	h := Handler(t.TempDir())
	for _, tc := range []struct{ host, origin string }{{"evil.test:7331", ""}, {"127.0.0.1.evil.test:7331", ""}, {"127.0.0.1:7331", "https://evil.test"}, {"127.0.0.1:7331", "http://127.0.0.1:7332"}} {
		if w := request(t, h, "GET", "/api/report", tc.host, tc.origin); w.Code != 403 {
			t.Fatalf("host=%q origin=%q status=%d", tc.host, tc.origin, w.Code)
		}
	}
	if w := request(t, h, "POST", "/api/report", "127.0.0.1:7331", ""); w.Code != 405 {
		t.Fatalf("POST status %d", w.Code)
	}
	if err := Serve(context.Background(), t.TempDir(), "0.0.0.0:7331", io.Discard); err == nil {
		t.Fatal("public bind allowed")
	}
}
