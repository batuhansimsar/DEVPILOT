package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDiscoverJVMBuild(t *testing.T) {
	for _, tc := range []struct {
		name  string
		files []string
		want  jvmBuild
	}{
		{"none", nil, jvmBuild{}},
		{"Maven", []string{"pom.xml"}, jvmBuild{Found: true, Tool: "Maven"}},
		{"Gradle Groovy", []string{"build.gradle"}, jvmBuild{Found: true, Tool: "Gradle"}},
		{"Gradle Kotlin DSL", []string{"build.gradle.kts"}, jvmBuild{Found: true, Tool: "Gradle"}},
		{"mixed builds", []string{"pom.xml", "build.gradle.kts"}, jvmBuild{Found: true, Conflict: true}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			for _, name := range tc.files {
				if err := os.WriteFile(filepath.Join(root, name), []byte("manifest"), 0600); err != nil {
					t.Fatal(err)
				}
			}
			got := discoverJVMBuild(root)
			if got != tc.want {
				t.Fatalf("discoverJVMBuild() = %+v, want %+v", got, tc.want)
			}
		})
	}
}

func TestDiscoverJVMBuildIgnoresSymlink(t *testing.T) {
	root := t.TempDir()
	outside := filepath.Join(t.TempDir(), "pom.xml")
	if err := os.WriteFile(outside, []byte("manifest"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(root, "pom.xml")); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	if got := discoverJVMBuild(root); got.Found {
		t.Fatalf("symlink should not count as manifest: %+v", got)
	}
}
