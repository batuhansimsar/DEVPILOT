package analyze

import (
	"path/filepath"
	"testing"
)

func TestInspectSkipsCaseVariantGeneratedDirectories(t *testing.T) {
	for _, dirname := range []string{"Node_Modules", ".GIT", ".Terraform", "VENv", "DiSt", "OBJ"} {
		t.Run(dirname, func(t *testing.T) {
			root := t.TempDir()
			write(t, filepath.Join(root, "main.go"), "package main")
			write(t, filepath.Join(root, dirname, "nested", "secret.ts"), "// dependency")
			write(t, filepath.Join(root, dirname, "package.json"), "{}")

			report, err := Inspect(root)
			if err != nil {
				t.Fatal(err)
			}
			if report.FileCount != 1 || report.Truncated || len(report.Manifests) != 0 {
				t.Fatalf("dependency directory %q was scanned: %+v", dirname, report)
			}
			if len(report.Languages) != 1 || report.Languages[0].Name != "Go" || report.Languages[0].Files != 1 {
				t.Fatalf("unexpected source inventory for %q: %+v", dirname, report.Languages)
			}
		})
	}
}
