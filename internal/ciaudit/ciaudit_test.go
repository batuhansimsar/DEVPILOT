package ciaudit

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func file(t *testing.T, root, path, text string) {
	t.Helper()
	full := filepath.Join(root, path)
	if err := os.MkdirAll(filepath.Dir(full), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(full, []byte(text), 0644); err != nil {
		t.Fatal(err)
	}
}
func TestMutableActionReferences(t *testing.T) {
	root := t.TempDir()
	fullSHA := strings.Repeat("a", 40)
	file(t, root, ".github/workflows/build.yml", `name: test
jobs:
  test:
    steps:
      - uses: actions/checkout@v4
      - uses: 'actions/setup-go@`+fullSHA+`' # immutable
      - uses: ./local/action
      - uses: docker://alpine:3.20
      # - uses: ignored/repo@main
      - run: echo "uses: fake/action@v2"
`)
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if report.Workflows != 1 || report.Actions != 2 || report.ImmutableActions != 1 || len(report.Findings) != 1 {
		t.Fatalf("wrong counts: %+v", report)
	}
	if f := report.Findings[0]; f.Workflow != ".github/workflows/build.yml" || f.Line != 5 || f.Reference != "actions/checkout@v4" {
		t.Fatalf("wrong evidence: %+v", f)
	}
}
func TestDoesNotFollowWorkflowSymlinks(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink privileges on Windows")
	}
	root := t.TempDir()
	outside := t.TempDir()
	file(t, outside, "evil.yml", "- uses: org/evil@latest")
	folder := filepath.Join(root, ".github", "workflows")
	if err := os.MkdirAll(folder, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join(outside, "evil.yml"), filepath.Join(folder, "evil.yml")); err != nil {
		t.Skip(err)
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(report.Findings) != 0 || len(report.Skipped) != 1 {
		t.Fatalf("symlink followed: %+v", report)
	}
}
func TestNoActionsDirectory(t *testing.T) {
	report, err := Inspect(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if report.Workflows != 0 || report.Actions != 0 || len(report.Findings) != 0 {
		t.Fatalf("unexpected: %+v", report)
	}
}
func TestLimitAndMalformedReference(t *testing.T) {
	root := t.TempDir()
	file(t, root, ".github/workflows/large.yaml", strings.Repeat("x", maxWorkflowBytes+1))
	file(t, root, ".github/workflows/odd.yml", "- uses: local@head\n- uses: ${{ env.ACTION }}\n")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Skipped) != 1 || len(r.Findings) != 0 {
		t.Fatalf("expected incomplete scan without false alarms: %+v", r)
	}
}
