package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDotnetSolutionFilterRecognized(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "Focused.slnf"), []byte("{\"solution\":{\"path\":\"app.sln\",\"projects\":[]}}"), 0600); err != nil {
		t.Fatal(err)
	}
	got, err := discoverDotnet(dir)
	if err != nil {
		t.Fatal(err)
	}
	if !got.Found || got.TestTarget != filepath.Join(dir, "Focused.slnf") ||
		got.Ambiguous || len(got.Languages) != 1 || got.Languages[0] != ".NET" {
		t.Fatalf("unexpected solution filter detection: %+v", got)
	}
}

func TestDotnetSolutionAndFilterAmbiguous(t *testing.T) {
	dir := t.TempDir()
	for _, name := range []string{"App.sln", "Focused.slnf"} {
		if err := os.WriteFile(filepath.Join(dir, name), nil, 0600); err != nil {
			t.Fatal(err)
		}
	}
	got, err := discoverDotnet(dir)
	if err != nil {
		t.Fatal(err)
	}
	if !got.Found || !got.Ambiguous || got.TestTarget != "" {
		t.Fatalf("expected ambiguous solution target, got %+v", got)
	}
}
