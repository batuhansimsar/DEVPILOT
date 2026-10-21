package doctor

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestDoctorDiscoversDenoProjects(t *testing.T) {
	for _, manifest := range []string{"deno.json", "deno.jsonc"} {
		t.Run(manifest, func(t *testing.T) {
			root := t.TempDir()
			write(t, root, manifest, "{}")
			r, err := Inspect(root)
			if err != nil {
				t.Fatal(err)
			}
			if len(r.Languages) != 1 || r.Languages[0] != "JavaScript/TypeScript" {
				t.Fatalf("languages: %v", r.Languages)
			}
			if len(r.Frameworks) != 1 || r.Frameworks[0] != "Deno" {
				t.Fatalf("frameworks: %v", r.Frameworks)
			}
			if r.Tests == nil || r.Tests.Executable != "deno" || len(r.Tests.Arguments) != 1 || r.Tests.Arguments[0] != "test" {
				t.Fatalf("test command: %+v", r.Tests)
			}
			if finding(r, "unknown-project") || !finding(r, "test-discovered") {
				t.Fatalf("unexpected findings: %+v", r.Findings)
			}
		})
	}
}

func TestDoctorDenoPreservesExistingTestRunner(t *testing.T) {
	root := t.TempDir()
	write(t, root, "package.json", `{"scripts":{"test":"node --test"}}`)
	write(t, root, "deno.json", "{}")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if r.Tests == nil || r.Tests.Executable != "npm" {
		t.Fatalf("existing Node test command should take precedence: %+v", r.Tests)
	}
	if len(r.Frameworks) != 1 || r.Frameworks[0] != "Deno" {
		t.Fatalf("Deno project was not recognized: %v", r.Frameworks)
	}
}

func TestDoctorDenoDoesNotFollowSymlink(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink privileges on Windows")
	}
	root := t.TempDir()
	outside := filepath.Join(t.TempDir(), "deno.json")
	if err := os.WriteFile(outside, []byte("{}"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(root, "deno.json")); err != nil {
		t.Fatal(err)
	}
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Languages) != 0 || r.Tests != nil {
		t.Fatalf("symlinked Deno config must be ignored: %+v", r)
	}
}
