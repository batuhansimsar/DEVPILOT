package analyze

import (
	"os"
	"path/filepath"
	"testing"
)

func TestProjectRootRejectsSymbolicLinkAncestor(t *testing.T) {
	base := t.TempDir()
	real := filepath.Join(base, "real")
	if err := os.MkdirAll(filepath.Join(real, "nested"), 0700); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(base, "link")
	if err := os.Symlink(real, link); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	if _, err := projectRoot(filepath.Join(link, "nested")); err == nil {
		t.Fatal("accepted a project accessed through a symlinked ancestor")
	}
	if _, err := projectRoot(filepath.Join(real, "nested")); err != nil {
		t.Fatalf("rejected real project: %v", err)
	}
}
