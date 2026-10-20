package analyze

import (
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
)

func TestInspectDiscoversAdditionalCIProviders(t *testing.T) {
	root := t.TempDir()
	files := []string{
		".circleci/config.yml", "bitbucket-pipelines.yml", ".travis.yml",
		".drone.yml", ".buildkite/pipeline.yaml", ".github/workflows/build.yml",
	}
	for _, file := range files {
		path := filepath.Join(root, filepath.FromSlash(file))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte("test: true\n"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	want := append([]string(nil), files...)
	sort.Strings(want)
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(report.CI, want) {
		t.Fatalf("CI files = %q, want %q", report.CI, want)
	}
}
