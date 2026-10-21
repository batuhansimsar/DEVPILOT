package analyze

import (
	"os"
	"path/filepath"
	"testing"
)

func TestInspectRecognizesDeclarativeSourceLanguages(t *testing.T) {
	root := t.TempDir()
	files := []string{
		"infra/main.tf", "infra/staging.TFVARS",
		"schema/messages.proto", "api/public.GRAPHQL", "api/internal.gql",
		"db/schema.prisma", "nix/default.nix", "validation/policy.cue", "notes.txt",
	}
	for _, name := range files {
		path := filepath.Join(root, name)
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte("example"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if report.Truncated || report.FileCount != len(files) {
		t.Fatalf("unexpected scan bounds: %+v", report)
	}
	got := make(map[string]int)
	for _, item := range report.Languages {
		got[item.Name] = item.Files
	}
	want := map[string]int{"Terraform": 2, "GraphQL": 2, "Protocol Buffers": 1, "Prisma": 1, "Nix": 1, "CUE": 1}
	if len(got) != len(want) {
		t.Fatalf("languages = %#v, want %#v", got, want)
	}
	for language, count := range want {
		if got[language] != count {
			t.Errorf("%s count = %d, want %d", language, got[language], count)
		}
	}
}
