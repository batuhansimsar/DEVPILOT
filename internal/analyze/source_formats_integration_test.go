package analyze

import (
	"os"
	"path/filepath"
	"testing"
)

func TestInspectSupplementalSourceFormats(t *testing.T) {
	root := t.TempDir()
	files := []string{
		"notebooks/analysis.ipynb", "notebooks/NOTEBOOK.IPYNB",
		"schema/api.proto", "graphql/schema.graphql", "graphql/queries.GQL",
		"contracts/token.sol", "nix/flake.nix", "README.md",
		"node_modules/ignored.proto",
	}
	for _, name := range files {
		path := filepath.Join(root, name)
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte("source content need not be parsed"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	got := map[string]int{}
	for _, entry := range report.Languages {
		got[entry.Name] = entry.Files
	}
	want := map[string]int{
		"Jupyter Notebook": 2,
		"Protocol Buffers": 1,
		"GraphQL":          2,
		"Solidity":         1,
		"Nix":              1,
	}
	if report.FileCount != len(files)-1 { // node_modules is excluded.
		t.Fatalf("file count: got %d, want %d", report.FileCount, len(files)-1)
	}
	if len(got) != len(want) {
		t.Fatalf("language inventory: got %#v, want %#v", got, want)
	}
	for name, count := range want {
		if got[name] != count {
			t.Errorf("%s: got %d, want %d", name, got[name], count)
		}
	}
}
