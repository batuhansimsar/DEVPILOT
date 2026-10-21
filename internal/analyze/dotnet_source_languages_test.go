package analyze

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

// A .NET workspace can contain F# and Visual Basic source files even when
// its project manifests are in separate directories.
func TestInspectDotnetSourceLanguageCounts(t *testing.T) {
	root := t.TempDir()
	for _, name := range []string{
		"src/Main.fs", "src/Contracts.fsi", "scripts/Bootstrap.fsx", "src/Form.vb",
		"src/Another.VB", "src/Program.cs", "src/App.fsproj", "src/Other.vbproj",
	} {
		file := filepath.Join(root, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(file), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(file, []byte("fixture"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if report.FileCount != 8 {
		t.Fatalf("file count = %d, want 8", report.FileCount)
	}
	got := map[string]int{}
	for _, language := range report.Languages {
		got[language.Name] = language.Files
	}
	want := map[string]int{"F#": 3, "Visual Basic": 2, "C#": 1}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("languages = %v, want %v", got, want)
	}
	if len(report.Manifests) != 2 {
		t.Fatalf("manifests = %v, want 2 dotnet projects", report.Manifests)
	}
}
