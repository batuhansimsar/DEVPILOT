package doctor

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestDetectJSLockfiles(t *testing.T) {
	cases := []struct {
		name    string
		files   []string
		manager string
	}{
		{"no lockfile", nil, "npm"},
		{"pnpm", []string{"pnpm-lock.yaml"}, "pnpm"},
		{"npm shrinkwrap", []string{"npm-shrinkwrap.json"}, "npm"},
		{"conflicting files", []string{"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}, "pnpm"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			for _, f := range tc.files {
				if err := os.WriteFile(filepath.Join(root, f), []byte("lock"), 0600); err != nil {
					t.Fatal(err)
				}
			}
			manager, exe, got := detectJSLockfiles(root)
			if manager != tc.manager || exe != tc.manager {
				t.Fatalf("manager=%q exe=%q; want %q", manager, exe, tc.manager)
			}
			if len(got) != len(tc.files) {
				t.Fatalf("found %v; want %v", got, tc.files)
			}
			_, _, repeat := detectJSLockfiles(root)
			if !reflect.DeepEqual(got, repeat) {
				t.Fatalf("unstable order: %v and %v", got, repeat)
			}
		})
	}
}

func TestDetectJSLockfilesSkipsSymlinks(t *testing.T) {
	root := t.TempDir()
	dst := filepath.Join(t.TempDir(), "outside")
	if err := os.WriteFile(dst, []byte("lock"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(dst, filepath.Join(root, "pnpm-lock.yaml")); err != nil {
		t.Skipf("symlink unsupported: %v", err)
	}
	manager, _, files := detectJSLockfiles(root)
	if manager != "npm" || len(files) != 0 {
		t.Fatalf("symlink must be ignored: manager=%q files=%v", manager, files)
	}
}

func TestConflictingJSLockfiles(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "package.json", "{}")
	write(t, dir, "pnpm-lock.yaml", "lockfileVersion: '9.0'")
	write(t, dir, "package-lock.json", "{}")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if !finding(r, "js-lockfiles-conflict") || !r.HasWarnings() {
		t.Fatalf("expected conflict warning, got %+v", r.Findings)
	}
	if r.PackageManager != "pnpm" {
		t.Fatalf("expected pnpm precedence, got %q", r.PackageManager)
	}
	for _, f := range r.Findings {
		if f.Code == "js-lockfiles-conflict" && (!strings.Contains(f.Message, "pnpm-lock.yaml") || !strings.Contains(f.Message, "package-lock.json")) {
			t.Fatalf("lockfile names absent from finding: %q", f.Message)
		}
	}
}

func TestSingleJSLockfileNoConflict(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "package.json", "{}")
	write(t, dir, "yarn.lock", "version 1")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if finding(r, "js-lockfiles-conflict") {
		t.Fatalf("unexpected conflict: %+v", r.Findings)
	}
}
