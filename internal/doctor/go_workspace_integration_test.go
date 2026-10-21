package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestInspectStandaloneGoWorkspace(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.work"), []byte("go 1.23\n\nuse ./service\n"), 0600); err != nil {
		t.Fatal(err)
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(report.Languages) != 1 || report.Languages[0] != "Go" {
		t.Fatalf("workspace should be recognized as Go: %+v", report.Languages)
	}
	if report.Tests != nil {
		t.Fatalf("workspace root is not a module; unsafe test command suggested: %+v", report.Tests)
	}
	if !hasGoWorkspaceFinding(report, "go-workspace-no-root-module") || hasGoWorkspaceFinding(report, "unknown-project") {
		t.Fatalf("unexpected workspace findings: %+v", report.Findings)
	}
}

func TestInspectGoWorkspaceWithRootModule(t *testing.T) {
	root := t.TempDir()
	for _, file := range []string{"go.mod", "go.work"} {
		if err := os.WriteFile(filepath.Join(root, file), []byte("go 1.23\n"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if report.Tests == nil || report.Tests.Executable != "go" || len(report.Tests.Arguments) != 2 || report.Tests.Arguments[0] != "test" || report.Tests.Arguments[1] != "./..." {
		t.Fatalf("root module test command not preserved: %+v", report.Tests)
	}
	if hasGoWorkspaceFinding(report, "go-workspace-no-root-module") {
		t.Fatalf("workspace-only advice should not appear for a root module: %+v", report.Findings)
	}
}

func hasGoWorkspaceFinding(report Report, code string) bool {
	for _, finding := range report.Findings {
		if finding.Code == code {
			return true
		}
	}
	return false
}
