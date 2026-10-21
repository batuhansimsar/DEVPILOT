package analyze

import (
	"os"
	"path/filepath"
	"testing"
)

func TestInspectModernNodeExtensions(t *testing.T) {
	root := t.TempDir()
	for _, name := range []string{
		"server.mjs", "config.cjs", "worker.MJS", "view.jsx",
		"main.mts", "util.cts", "types.CTS", "main.tsx", "notes.json",
	} {
		if err := os.WriteFile(filepath.Join(root, name), []byte("test"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if report.FileCount != 9 {
		t.Fatalf("file count = %d, want 9", report.FileCount)
	}
	got := make(map[string]int, len(report.Languages))
	for _, language := range report.Languages {
		got[language.Name] = language.Files
	}
	if got["JavaScript"] != 4 || got["TypeScript"] != 4 || len(got) != 2 {
		t.Fatalf("language counts = %#v, want JavaScript=4 and TypeScript=4", got)
	}
}
