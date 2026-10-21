package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDiscoverJVMBuildSettingsOnly(t *testing.T) {
	for _, marker := range []string{"settings.gradle", "settings.gradle.kts"} {
		t.Run(marker, func(t *testing.T) {
			root := t.TempDir()
			if err := os.WriteFile(filepath.Join(root, marker), []byte("include('app')"), 0600); err != nil {
				t.Fatal(err)
			}
			if got := discoverJVMBuild(root); got != (jvmBuild{Found: true, Tool: "Gradle"}) {
				t.Fatalf("settings-only root: got %+v", got)
			}
		})
	}
}

func TestDiscoverJVMBuildSettingsAndMavenConflict(t *testing.T) {
	root := t.TempDir()
	for _, marker := range []string{"settings.gradle.kts", "pom.xml"} {
		if err := os.WriteFile(filepath.Join(root, marker), []byte("manifest"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	if got := discoverJVMBuild(root); got != (jvmBuild{Found: true, Conflict: true}) {
		t.Fatalf("mixed Maven and Gradle settings should be ambiguous: got %+v", got)
	}
}

func TestDiscoverJVMBuildIgnoresUnsafeSettingsEntries(t *testing.T) {
	for _, marker := range []string{"settings.gradle", "settings.gradle.kts"} {
		t.Run(marker+" directory", func(t *testing.T) {
			root := t.TempDir()
			if err := os.Mkdir(filepath.Join(root, marker), 0700); err != nil {
				t.Fatal(err)
			}
			if got := discoverJVMBuild(root); got.Found {
				t.Fatalf("directory must not select Gradle: %+v", got)
			}
		})
		t.Run(marker+" symlink", func(t *testing.T) {
			root := t.TempDir()
			outside := filepath.Join(t.TempDir(), "outside")
			if err := os.WriteFile(outside, []byte("outside"), 0600); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink(outside, filepath.Join(root, marker)); err != nil {
				t.Skipf("symlinks unavailable: %v", err)
			}
			if got := discoverJVMBuild(root); got.Found {
				t.Fatalf("symlink must not select Gradle: %+v", got)
			}
		})
	}
}
