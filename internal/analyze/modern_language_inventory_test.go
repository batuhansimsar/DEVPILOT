package analyze

import (
	"os"
	"path/filepath"
	"testing"
)

func TestInspectRecognizesModernLanguageSources(t *testing.T) {
	root := t.TempDir()
	files := []string{
		"main.zig", "server.ex", "config.exs", "analysis.jl",
		"Main.scala", "script.sc", "Main.hs", "legacy.lhs",
		"core.clj", "browser.cljs", "shared.cljc",
		"stats.R", "report.Rmd", "Program.purs",
		"Main.elm", "config.lua", "Pipeline.groovy",
	}
	for _, name := range files {
		if err := os.WriteFile(filepath.Join(root, name), []byte("// source"), 0600); err != nil {
			t.Fatal(err)
		}
	}

	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	got := make(map[string]int)
	for _, language := range report.Languages {
		got[language.Name] = language.Files
	}
	want := map[string]int{
		"Zig": 1, "Elixir": 2, "Julia": 1, "Scala": 2,
		"Haskell": 2, "Clojure": 2, "ClojureScript": 1,
		"R": 2, "PureScript": 1, "Elm": 1, "Lua": 1, "Groovy": 1,
	}
	if report.FileCount != len(files) {
		t.Fatalf("file count = %d, want %d", report.FileCount, len(files))
	}
	if len(got) != len(want) {
		t.Fatalf("language inventory = %#v, want %#v", got, want)
	}
	for name, count := range want {
		if got[name] != count {
			t.Errorf("%s files = %d, want %d", name, got[name], count)
		}
	}
}
