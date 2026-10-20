package doctor

import (
	"os"
	"path/filepath"
	"slices"
	"testing"
)

func TestDotnetSolutionOnlyLanguage(t *testing.T) {
	for _, ext := range []string{".sln", ".slnx"} {
		t.Run(ext, func(t *testing.T) {
			dir := t.TempDir()
			name := "Workspace" + ext
			if err := os.WriteFile(filepath.Join(dir, name), []byte(""), 0600); err != nil {
				t.Fatal(err)
			}
			got, err := discoverDotnet(dir)
			if err != nil {
				t.Fatal(err)
			}
			if !slices.Equal(got.Languages, []string{".NET"}) || got.TestTarget != filepath.Join(dir, name) || !got.Found || got.Ambiguous {
				t.Fatalf("solution-only workspace: %+v", got)
			}
		})
	}
}
