package analyze

import (
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
)

func TestAnalyzeDetectsPytestConfigurationManifests(t *testing.T) {
	root := t.TempDir()
	files := []string{".pytest.ini", ".pytest.toml", "pytest.ini", "pytest.toml", "services/api/pytest.toml"}
	want := make([]string, 0, len(files))
	for _, name := range files {
		path := filepath.Join(root, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, nil, 0600); err != nil {
			t.Fatal(err)
		}
		want = append(want, name+" (Python)")
	}
	sort.Strings(want)
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(report.Manifests, want) {
		t.Fatalf("manifests = %v, want %v", report.Manifests, want)
	}
}
