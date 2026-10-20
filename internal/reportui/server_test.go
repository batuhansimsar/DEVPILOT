package reportui

import (
	"errors"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestLocalReadOnlyDoctorAPI(t *testing.T) {
	calls := 0
	handler := Handler("/tmp/example", func(path string) (any, error) {
		calls++
		if path != "/tmp/example" {
			t.Fatalf("unexpected path %q", path)
		}
		return map[string]any{"path": path, "findings": []any{}}, nil
	})
	tests := []struct {
		method, path, host string
		want               int
	}{{"GET", "/api/doctor", "localhost:3847", 200}, {"POST", "/api/doctor", "localhost:3847", 405}, {"GET", "/api/doctor", "attacker.example:3847", 403}, {"GET", "/", "127.0.0.1:3847", 200}}
	for _, tc := range tests {
		req := httptest.NewRequest(tc.method, tc.path, nil)
		req.Host = tc.host
		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)
		if rec.Code != tc.want {
			t.Errorf("%s %s %s: got %d want %d", tc.method, tc.path, tc.host, rec.Code, tc.want)
		}
		if rec.Header().Get("Content-Security-Policy") == "" {
			t.Error("missing CSP")
		}
		if tc.method == "GET" && tc.path == "/api/doctor" && tc.want == 200 && !strings.Contains(rec.Body.String(), "/tmp/example") {
			t.Error("invalid report")
		}
	}
	if calls != 1 {
		t.Fatalf("expected one inspection, got %d", calls)
	}
}
func TestInspectorErrorDoesNotLeakDetails(t *testing.T) {
	handler := Handler(".", func(string) (any, error) { return nil, errors.New("TOP_SECRET") })
	req := httptest.NewRequest("GET", "/api/doctor", nil)
	req.Host = "localhost"
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != 500 || strings.Contains(rec.Body.String(), "TOP_SECRET") {
		t.Fatal("internal details leaked")
	}
}
