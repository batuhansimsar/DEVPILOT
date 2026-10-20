package envcheck

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func write(t *testing.T, root, name, content string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(root, name), []byte(content), 0600); err != nil {
		t.Fatal(err)
	}
}

func emptyLookup(string) (string, bool) { return "", false }

func TestCheckSourcesAndNoSecretValues(t *testing.T) {
	root := t.TempDir()
	write(t, root, ".env.example", "# documented\nexport API_KEY=placeholder\nDATABASE_URL=\nCACHE_HOST=\n")
	write(t, root, ".env.local.example", "CACHE_HOST=localhost\n")
	write(t, root, ".env", "DATABASE_URL=postgres://admin:hunter2@local/db\nCACHE_HOST= # blank\n")
	report, err := Check(root, func(k string) (string, bool) {
		if k == "API_KEY" {
			return "super-secret-value", true
		}
		return "", false
	})
	if err != nil {
		t.Fatal(err)
	}
	if report.Summary != (Summary{Total: 3, InProcess: 1, InDotEnv: 1, Unconfigured: 1}) {
		t.Fatalf("unexpected summary: %+v", report.Summary)
	}
	if report.Variables[0].Name != "API_KEY" || report.Variables[1].Name != "CACHE_HOST" || len(report.Variables[1].Templates) != 2 {
		t.Fatalf("deduplication failed: %+v", report.Variables)
	}
	b, err := json.Marshal(report)
	if err != nil {
		t.Fatal(err)
	}
	for _, secret := range []string{"hunter2", "super-secret-value", "placeholder"} {
		if strings.Contains(string(b), secret) {
			t.Fatalf("secret %q leaked into report", secret)
		}
	}
}

func TestNoTemplatesIsNotAFailure(t *testing.T) {
	r, err := Check(t.TempDir(), emptyLookup)
	if err != nil || r.Summary.Total != 0 || len(r.Variables) != 0 {
		t.Fatalf("got report=%+v error=%v", r, err)
	}
}

func TestDotEnvSymlinkIsIgnored(t *testing.T) {
	root := t.TempDir()
	outside := t.TempDir()
	write(t, root, ".env.example", "PASSWORD=\n")
	write(t, outside, "outside", "PASSWORD=do-not-read\n")
	if err := os.Symlink(filepath.Join(outside, "outside"), filepath.Join(root, ".env")); err != nil {
		t.Skipf("symlink unsupported: %v", err)
	}
	r, err := Check(root, emptyLookup)
	if err != nil || r.Summary.Unconfigured != 1 {
		t.Fatalf("unexpected symlink result: %+v %v", r, err)
	}
}

func TestTemplateSymlinkIsIgnored(t *testing.T) {
	root := t.TempDir()
	outside := t.TempDir()
	write(t, outside, "outside", "PASSWORD=foo\n")
	if err := os.Symlink(filepath.Join(outside, "outside"), filepath.Join(root, ".env.example")); err != nil {
		t.Skipf("symlink unsupported: %v", err)
	}
	r, err := Check(root, emptyLookup)
	if err != nil || r.Summary.Total != 0 {
		t.Fatalf("unexpected template symlink result: %+v %v", r, err)
	}
}

func TestRejectsOversizedFile(t *testing.T) {
	root := t.TempDir()
	write(t, root, ".env.example", strings.Repeat("A", maxFileSize+1))
	if _, err := Check(root, emptyLookup); err == nil || !strings.Contains(err.Error(), "exceeds") {
		t.Fatalf("expected size limit error, got %v", err)
	}
}

func TestParseAssignment(t *testing.T) {
	for _, tc := range []struct {
		line string
		key  string
		set  bool
	}{
		{"export DB_URL=postgres://db#fragment", "DB_URL", true},
		{"API_KEY= # missing", "API_KEY", false},
		{"SECRET=\"  \"", "SECRET", false},
		{"_TOKEN='abc#123' # comment", "_TOKEN", true},
		{"not a variable", "", false},
		{"2BAD=bad", "", false},
		{"# DB_URL=ignored", "", false},
	} {
		name, val, ok := parseAssignment(tc.line)
		if name != tc.key || (ok && hasValue(val)) != tc.set {
			t.Errorf("line %q: name=%q ok=%t valuePresent=%t", tc.line, name, ok, hasValue(val))
		}
	}
}
