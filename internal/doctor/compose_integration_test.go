package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestComposeDiagnosticsIntegrated(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "compose.yaml"), []byte("services: {}"), 0600); err != nil {
		t.Fatal(err)
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !finding(report, "docker-compose-found") {
		t.Fatalf("missing Compose diagnostics in doctor: %+v", report.Findings)
	}
}
