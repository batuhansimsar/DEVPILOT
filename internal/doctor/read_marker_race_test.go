package doctor

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

// The post-open identity check prevents a rename or symlink swap between
// Lstat and Open from reading an unexpected file.
func TestReadMarkerAfterStatStableFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "package.json")
	if err := os.WriteFile(path, []byte("safe"), 0600); err != nil {
		t.Fatal(err)
	}
	stat, err := os.Lstat(path)
	if err != nil {
		t.Fatal(err)
	}
	data, found, err := readMarkerAfterStat(path, "package.json", stat)
	if err != nil || !found || string(data) != "safe" {
		t.Fatalf("data=%q found=%v err=%v", data, found, err)
	}
}

func TestReadMarkerAfterStatRejectsRegularFileSwap(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "package.json")
	if err := os.WriteFile(path, []byte("safe"), 0600); err != nil {
		t.Fatal(err)
	}
	stat, err := os.Lstat(path)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Rename(path, path+".old"); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte("secret"), 0600); err != nil {
		t.Fatal(err)
	}
	data, found, err := readMarkerAfterStat(path, "package.json", stat)
	if err == nil || found || data != nil {
		t.Fatalf("must reject swapped regular file: data=%q found=%v err=%v", data, found, err)
	}
}

func TestReadMarkerAfterStatRejectsSymlinkSwap(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink permissions on Windows")
	}
	dir := t.TempDir()
	path := filepath.Join(dir, "package.json")
	outside := filepath.Join(t.TempDir(), "outside.json")
	if err := os.WriteFile(path, []byte("safe"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(outside, []byte("secret"), 0600); err != nil {
		t.Fatal(err)
	}
	stat, err := os.Lstat(path)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Rename(path, path+".old"); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, path); err != nil {
		t.Fatal(err)
	}
	data, found, err := readMarkerAfterStat(path, "package.json", stat)
	if err == nil || found || data != nil {
		t.Fatalf("must reject swapped symlink: data=%q found=%v err=%v", data, found, err)
	}
}
