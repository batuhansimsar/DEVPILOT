package analyze

import (
	"os"
	"path/filepath"
	"testing"
)

func TestInspectDetectsPipfileLockManifest(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "Pipfile.lock"), []byte("{}"), 0600); err != nil {
		t.Fatal(err)
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	for _, manifest := range report.Manifests {
		if manifest == "Pipfile.lock (Python)" {
			return
		}
	}
	t.Fatalf("expected Pipfile.lock Python manifest, got %v", report.Manifests)
}
