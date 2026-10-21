package analyze

import (
	"errors"
	"fmt"
	"io/fs"
	"path/filepath"
	"strings"
	"testing"
)

func TestWalkWarningRedactsRawFilesystemErrors(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "subdir", "missing.ts")
	cases := []struct {
		name, want string
		err        error
	}{
		{"permission", "permission denied", fmt.Errorf("/private/key: password=secret: %w", fs.ErrPermission)},
		{"missing", "path no longer exists", fmt.Errorf("/private/key: password=secret: %w", fs.ErrNotExist)},
		{"other", "filesystem error", errors.New("/private/key: password=secret")},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := walkWarning(root, path, tc.err)
			if !strings.Contains(got, "\"subdir/missing.ts\"") || !strings.HasSuffix(got, ": "+tc.want) {
				t.Fatalf("unexpected warning: %q", got)
			}
			if strings.Contains(got, root) || strings.Contains(got, "private") || strings.Contains(got, "secret") {
				t.Fatalf("sensitive error details leaked: %q", got)
			}
		})
	}
}

func TestWalkWarningEscapesUntrustedPathCharacters(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "bad\nname\x1b\u202e.ts")
	got := walkWarning(root, path, fs.ErrPermission)
	if strings.Contains(got, "\n") || strings.Contains(got, "\x1b") || strings.Contains(got, "\u202e") {
		t.Fatalf("control or bidi codepoints leaked: %q", got)
	}
	for _, escaped := range []string{"\\n", "\\x1b", "\\u202e"} {
		if !strings.Contains(got, escaped) {
			t.Errorf("missing expected quoted escape %q in %q", escaped, got)
		}
	}
}

func TestWalkWarningHidesPathsOutsideProject(t *testing.T) {
	root := filepath.Join(t.TempDir(), "project")
	outside := filepath.Join(filepath.Dir(root), "private", "token")
	got := walkWarning(root, outside, fmt.Errorf("secret: %w", fs.ErrPermission))
	if got != "Cannot inspect \".\": permission denied" {
		t.Fatalf("unexpected out-of-root warning: %q", got)
	}
}
