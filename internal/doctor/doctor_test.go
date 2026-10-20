package doctor

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

func writeFile(t *testing.T, root, name, content string) {
	t.Helper()
	path := filepath.Join(root, name)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
}
func containsCode(findings []Finding, code string) bool {
	for _, f := range findings {
		if f.Code == code {
			return true
		}
	}
	return false
}
func hasDetection(detections []Detection, name string) bool {
	for _, d := range detections {
		if d.Name == name {
			return true
		}
	}
	return false
}
func analyze(t *testing.T, root string) Report {
	t.Helper()
	r, e := Analyze(context.Background(), root, Options{})
	if e != nil {
		t.Fatal(e)
	}
	return r
}

func TestGoAndJavaScriptDetection(t *testing.T) {
	root := t.TempDir()
	writeFile(t, root, "go.mod", "module example.com/demo\n\ngo 1.23\n")
	writeFile(t, root, "web/package.json", `{"scripts":{"test":"vitest run"},"dependencies":{"react":"*"},"devDependencies":{"vitest":"*","typescript":"*"}}`)
	writeFile(t, root, "web/package-lock.json", "{}")
	r := analyze(t, root)
	for _, name := range []string{"Go", "Node.js", "React", "Vitest", "TypeScript"} {
		if !hasDetection(r.Detections, name) {
			t.Errorf("missing detection: %s", name)
		}
	}
	if len(r.TestCommands) != 2 {
		t.Fatalf("wanted two test commands, got %+v", r.TestCommands)
	}
	if len(r.TestResults) != 0 {
		t.Fatal("tests must not execute by default")
	}
}

func TestLockfileEvidence(t *testing.T) {
	root := t.TempDir()
	writeFile(t, root, "package.json", `{"name":"demo"}`)
	writeFile(t, root, "yarn.lock", "")
	writeFile(t, root, "package-lock.json", "{}")
	r := analyze(t, root)
	if !containsCode(r.Findings, "MULTIPLE_LOCKFILES") {
		t.Fatalf("missing lockfile warning: %+v", r.Findings)
	}
}

func TestInvalidManifestNotAFramework(t *testing.T) {
	root := t.TempDir()
	writeFile(t, root, "package.json", "not json")
	r := analyze(t, root)
	if !containsCode(r.Findings, "MANIFEST_INVALID") {
		t.Fatal("expected malformed manifest warning")
	}
	if hasDetection(r.Detections, "React") {
		t.Fatal("should not infer React from malformed manifest")
	}
}

func TestEnvNeverPrintsSecrets(t *testing.T) {
	root := t.TempDir()
	writeFile(t, root, ".env.example", "# Example\nAPI_TOKEN=super-sensitive-value\nPORT=4000\n")
	r := analyze(t, root)
	if !containsCode(r.Findings, "ENV_TEMPLATE_FOUND") {
		t.Fatal("expected environment template notice")
	}
	if strings.Contains(strings.Join(findingMessages(r.Findings), " "), "super-sensitive-value") {
		t.Fatal("secret leaked into report")
	}
}
func findingMessages(fs []Finding) []string {
	var out []string
	for _, f := range fs {
		out = append(out, f.Message, f.Remedy, strings.Join(f.Evidence, ","))
	}
	return out
}

func TestWorkspaceTrustRequired(t *testing.T) {
	root := t.TempDir()
	writeFile(t, root, "go.mod", "module example.com/test\n\ngo 1.23\n")
	_, err := Analyze(context.Background(), root, Options{RunTests: true})
	if err == nil || !strings.Contains(err.Error(), "trust-workspace") {
		t.Fatalf("expected consent requirement: %v", err)
	}
}

func TestSymlinksSkipped(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink creation requires OS privileges")
	}
	root := t.TempDir()
	other := t.TempDir()
	writeFile(t, other, "go.mod", "module example.com/outside\n")
	if err := os.Symlink(other, filepath.Join(root, "injected")); err != nil {
		t.Skipf("cannot create symlink: %v", err)
	}
	r := analyze(t, root)
	if hasDetection(r.Detections, "Go") {
		t.Fatal("must not read symlinked folder outside workspace")
	}
}

func TestTestRunnerExecutesOnlyWithConsent(t *testing.T) {
	if _, err := exec.LookPath("go"); err != nil {
		t.Skip("Go executable unavailable")
	}
	root := t.TempDir()
	writeFile(t, root, "go.mod", "module example.com/sample\n\ngo 1.23.0\n")
	writeFile(t, root, "sample_test.go", "package sample\nimport \"testing\"\nfunc TestOne(t *testing.T){}\n")
	r, err := Analyze(context.Background(), root, Options{RunTests: true, TrustWorkspace: true, Timeout: 30 * time.Second})
	if err != nil {
		t.Fatal(err)
	}
	if len(r.TestResults) != 1 || !r.TestResults[0].Passed {
		t.Fatalf("test execution failed: %+v", r.TestResults)
	}
}

func TestMissingWorkspace(t *testing.T) {
	_, err := Analyze(context.Background(), filepath.Join(t.TempDir(), "nonexistent"), Options{})
	if err == nil {
		t.Fatal("missing workspace should be rejected")
	}
}

func TestNestedDiscoveryBounded(t *testing.T) {
	root := t.TempDir()
	writeFile(t, root, "apps/api/deep/go.mod", "module example.com/deep\n")
	r := analyze(t, root)
	if hasDetection(r.Detections, "Go") {
		t.Fatal("nested beyond depth 2 should not be traversed")
	}
}

func TestSecretRedaction(t *testing.T) {
	t.Setenv("DEVPILOT_TEST_API_KEY", "VerySensitiveToken12345")
	input := "password=abc123\ntoken: something\napi_key=XYZ\nVerySensitiveToken12345\nghp_1234567890ABCDEFGHIJ"
	output := redactSecrets(input)
	for _, hidden := range []string{"abc123", "something", "XYZ", "VerySensitiveToken12345", "ghp_1234567890ABCDEFGHIJ"} {
		if strings.Contains(output, hidden) {
			t.Errorf("redaction missed %q", hidden)
		}
	}
}
func TestLimitedOutput(t *testing.T) {
	capture := &limitedOutput{max: 4}
	if _, err := capture.Write([]byte("1234567890")); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(capture.String(), "1234") || !strings.Contains(capture.String(), "truncated") || strings.Contains(capture.String(), "5678") {
		t.Fatalf("failed to limit test output: %s", capture.String())
	}
}
