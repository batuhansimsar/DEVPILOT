package analyze

import (
	"os"
	"path/filepath"
	"testing"
)

func TestInspectRecognizesExtendedSourceExtensions(t *testing.T) {
	root := t.TempDir()
	files := []string{
		"include/a.hh", "include/b.HPP", "include/c.hxx",
		"src/main.cxx", "src/helper.c++", "src/module.ixx", "src/module.cppm",
		"build.gradle.kts", "tools/script.csx", "ios/View.mm",
		"typing/models.pyi", "bin/tool.PYW", "native/core.pyx",
		"native/header.pxd", "native/inline.pxi", "notes.json",
	}
	for _, name := range files {
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
	if report.FileCount != len(files) {
		t.Fatalf("file count = %d, want %d", report.FileCount, len(files))
	}
	got := make(map[string]int)
	for _, language := range report.Languages {
		got[language.Name] = language.Files
	}
	want := map[string]int{"C++": 7, "Kotlin": 1, "C#": 1, "Objective-C++": 1, "Python": 2, "Cython": 3}
	if len(got) != len(want) {
		t.Fatalf("languages = %#v, want %#v", got, want)
	}
	for language, count := range want {
		if got[language] != count {
			t.Errorf("%s count = %d, want %d", language, got[language], count)
		}
	}
}
