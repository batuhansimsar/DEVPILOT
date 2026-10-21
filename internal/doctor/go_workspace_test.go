package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestGoProjectMarkers(t *testing.T) {
	tests := []struct {
		name          string
		markers       []string
		wantModule    bool
		wantWorkspace bool
	}{
		{name: "empty"},
		{name: "module", markers: []string{"go.mod"}, wantModule: true},
		{name: "workspace", markers: []string{"go.work"}, wantWorkspace: true},
		{name: "both", markers: []string{"go.mod", "go.work"}, wantModule: true, wantWorkspace: true},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			for _, marker := range tc.markers {
				if err := os.WriteFile(filepath.Join(root, marker), []byte("go 1.23\n"), 0600); err != nil {
					t.Fatal(err)
				}
			}
			mod, work := goProjectMarkers(root)
			if mod != tc.wantModule || work != tc.wantWorkspace {
				t.Fatalf("goProjectMarkers() = (%v, %v), want (%v, %v)", mod, work, tc.wantModule, tc.wantWorkspace)
			}
		})
	}
}

func TestGoProjectMarkersIgnoresNonregularFiles(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "go.mod"), 0700); err != nil {
		t.Fatal(err)
	}
	external := filepath.Join(t.TempDir(), "go.work")
	if err := os.WriteFile(external, []byte("go 1.23\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(external, filepath.Join(root, "go.work")); err != nil {
		t.Skipf("symlinks unsupported: %v", err)
	}
	module, workspace := goProjectMarkers(root)
	if module || workspace {
		t.Fatalf("nonregular markers must be ignored: module=%v workspace=%v", module, workspace)
	}
}
