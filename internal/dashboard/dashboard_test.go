package dashboard

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

type finding struct{ Level, Code, Message, Remedy string }
type testCommand struct {
	Executable string
	Arguments  []string
}
type report struct {
	Path           string       `json:"path"`
	Languages      []string     `json:"languages"`
	Frameworks     []string     `json:"frameworks"`
	PackageManager string       `json:"package_manager"`
	Tests          *testCommand `json:"tests"`
	Findings       []finding    `json:"findings"`
}

func sample() (any, error) {
	return report{Path: "<img src=x onerror=alert(1)>", Languages: []string{"Go"}, Frameworks: []string{}, PackageManager: "", Tests: &testCommand{Executable: "go", Arguments: []string{"test", "./..."}}, Findings: []finding{{"warning", "sample", "<script>alert('x')</script>", "Fix it"}}}, nil
}
func TestRendersEscapedHTMLAndJSON(t *testing.T) {
	handler := Handler(sample)
	req := httptest.NewRequest(http.MethodGet, "http://127.0.0.1/", nil)
	resp := httptest.NewRecorder()
	handler.ServeHTTP(resp, req)
	if resp.Code != 200 {
		t.Fatalf("HTTP %d: %s", resp.Code, resp.Body.String())
	}
	body := resp.Body.String()
	if !strings.Contains(body, "Project overview") || !strings.Contains(body, "go test ./...") {
		t.Fatal("dashboard missing data")
	}
	if strings.Contains(body, "<script>") || strings.Contains(body, "<img src=x") {
		t.Fatal("untrusted data was inserted without escaping")
	}
	if !strings.Contains(body, "&lt;script&gt;") {
		t.Fatal("expected escaped finding")
	}
	if !strings.Contains(resp.Header().Get("Content-Security-Policy"), "default-src 'none'") {
		t.Fatal("missing CSP")
	}
	req = httptest.NewRequest(http.MethodGet, "http://localhost/api/report", nil)
	resp = httptest.NewRecorder()
	handler.ServeHTTP(resp, req)
	if resp.Code != 200 {
		t.Fatal(resp.Code)
	}
	var data map[string]any
	if err := json.Unmarshal(resp.Body.Bytes(), &data); err != nil || data["path"] == nil {
		t.Fatalf("invalid JSON: %v", err)
	}
}
func TestNoRemoteHostsOrMutations(t *testing.T) {
	handler := Handler(sample)
	for _, tc := range []struct {
		method, path, host string
		status             int
	}{{"GET", "/", "evil.example", 403}, {"POST", "/", "localhost", 405}, {"GET", "/missing", "localhost", 404}, {"PUT", "/api/report", "127.0.0.1", 405}} {
		req := httptest.NewRequest(tc.method, "http://127.0.0.1"+tc.path, nil)
		req.Host = tc.host
		resp := httptest.NewRecorder()
		handler.ServeHTTP(resp, req)
		if resp.Code != tc.status {
			t.Errorf("%s %s (%s): want %d, got %d", tc.method, tc.path, tc.host, tc.status, resp.Code)
		}
	}
}
func TestScanFailureIsGeneric(t *testing.T) {
	handler := Handler(func() (any, error) { return nil, errors.New("secret/private/path") })
	resp := httptest.NewRecorder()
	handler.ServeHTTP(resp, httptest.NewRequest("GET", "http://localhost/", nil))
	if resp.Code != 500 || strings.Contains(resp.Body.String(), "secret/private/path") {
		t.Fatalf("leaky failure %d %s", resp.Code, resp.Body.String())
	}
}
