package doctor

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestDotnetCSharpProject(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "App.csproj", "<Project />")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Languages) != 1 || r.Languages[0] != "C#" || len(r.Frameworks) != 1 || r.Frameworks[0] != ".NET" {
		t.Fatalf("unexpected .NET detection: %+v", r)
	}
	if r.Tests == nil || r.Tests.Executable != "dotnet" ||
		strings.Join(r.Tests.Arguments, "|") != "test|"+filepath.Join(dir, "App.csproj") {
		t.Fatalf("unexpected test discovery: %+v", r.Tests)
	}
}

func TestDotnetSolutionPreferred(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "Demo.slnx", "")
	write(t, dir, "App.csproj", "<Project />")
	write(t, dir, "Tests.csproj", "<Project />")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if r.Tests == nil || r.Tests.Executable != "dotnet" ||
		strings.Join(r.Tests.Arguments, "|") != "test|"+filepath.Join(dir, "Demo.slnx") {
		t.Fatalf("solution target not selected: %+v", r.Tests)
	}
	if finding(r, "dotnet-ambiguous-target") {
		t.Fatalf("one solution should be unambiguous: %+v", r.Findings)
	}
}

func TestDotnetAmbiguousProjects(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "Api.csproj", "<Project />")
	write(t, dir, "App.csproj", "<Project />")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if r.Tests != nil || !finding(r, "dotnet-ambiguous-target") {
		t.Fatalf("multiple projects must not be guessed: %+v", r)
	}
}

func TestDotnetFSharpAndVB(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "App.fsproj", "<Project />")
	write(t, dir, "Worker.vbproj", "<Project />")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(r.Languages, ",") != "F#,Visual Basic" {
		t.Fatalf("unexpected languages: %v", r.Languages)
	}
	if !finding(r, "dotnet-ambiguous-target") {
		t.Fatalf("missing ambiguity finding: %+v", r.Findings)
	}
}

func TestDotnetSymlinkIgnored(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Windows symlink privileges vary by runner")
	}
	dir := t.TempDir()
	outside := filepath.Join(t.TempDir(), "Other.csproj")
	if err := os.WriteFile(outside, []byte("<Project />"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(dir, "Other.csproj")); err != nil {
		t.Fatal(err)
	}
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Languages) != 0 || len(r.Frameworks) != 0 || r.Tests != nil {
		t.Fatalf("symlink must not be detected: %+v", r)
	}
}

func TestDotnetTestDoesNotOverrideGo(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "go.mod", "module test\n\ngo 1.23\n")
	write(t, dir, "App.csproj", "<Project />")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if r.Tests == nil || r.Tests.Executable != "go" {
		t.Fatalf("existing test priority changed: %+v", r.Tests)
	}
}
