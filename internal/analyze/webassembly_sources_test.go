package analyze

import (
	"os"
	"path/filepath"
	"testing"
)

func TestInspectRecognizesWebAssemblySources(t *testing.T) {
	root := t.TempDir()
	filenames := []string{
		"module.wat", "tests.WAST", "interface.wit",
		"nested/component.WIT", "module.wat.bak", "README.md",
	}
	for _, name := range filenames {
		path := filepath.Join(root, name)
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte("source"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if report.Truncated || report.FileCount != len(filenames) {
		t.Fatalf("unexpected scan state: %+v", report)
	}
	counts := make(map[string]int)
	for _, item := range report.Languages {
		counts[item.Name] = item.Files
	}
	if counts["WebAssembly Text"] != 2 || counts["WebAssembly Interface Types"] != 2 || len(counts) != 2 {
		t.Fatalf("wrong WebAssembly inventory: %#v", counts)
	}
}
