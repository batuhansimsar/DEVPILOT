package doctor

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestReadMarkerStableSnapshot(t *testing.T) {
	p := filepath.Join(t.TempDir(), "package.json")
	if err := os.WriteFile(p, []byte(`{"scripts":{"test":"go test"}}`), 0600); err != nil {
		t.Fatal(err)
	}
	initial, err := os.Lstat(p)
	if err != nil {
		t.Fatal(err)
	}
	data, found, err := readMarkerAfterStat(p, "package.json", initial)
	if err != nil || !found || string(data) != `{"scripts":{"test":"go test"}}` {
		t.Fatalf("got %q, %v, %v", data, found, err)
	}
}

func TestReadMarkerRejectsInPlaceRewriteBetweenStatAndOpen(t *testing.T) {
	p := filepath.Join(t.TempDir(), "package.json")
	if err := os.WriteFile(p, []byte(`{"scripts":{}}`), 0600); err != nil {
		t.Fatal(err)
	}
	old := time.Unix(100, 0)
	if err := os.Chtimes(p, old, old); err != nil {
		t.Fatal(err)
	}
	initial, err := os.Lstat(p)
	if err != nil {
		t.Fatal(err)
	}
	// Rewriting in place preserves the inode and byte count. SameFile alone misses it.
	if err := os.WriteFile(p, []byte(`{"scripts":[]}`), 0600); err != nil {
		t.Fatal(err)
	}
	newer := time.Unix(200, 0)
	if err := os.Chtimes(p, newer, newer); err != nil {
		t.Fatal(err)
	}
	data, found, err := readMarkerAfterStat(p, "package.json", initial)
	if err == nil || found || data != nil || !strings.Contains(err.Error(), "changed while opening") {
		t.Fatalf("expected stale snapshot rejection, got %q %v %v", data, found, err)
	}
}
