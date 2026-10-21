package analyze

import (
	"io/fs"
	"path/filepath"
	"strings"
	"testing"
)

func TestWalkWarningBoundsLongRelativePaths(t *testing.T) {
	root := t.TempDir()
	cases := []struct {
		name string
		rel  string
		want string
	}{
		{"exact boundary", strings.Repeat("a", maxWalkWarningPathBytes), strings.Repeat("a", maxWalkWarningPathBytes)},
		{"one byte over", strings.Repeat("a", maxWalkWarningPathBytes+1), "... (path too long)"},
		{"unicode over", strings.Repeat("界", maxWalkWarningPathBytes/3+1), "... (path too long)"},
		{"control characters over", strings.Repeat("\x1b", maxWalkWarningPathBytes+1), "... (path too long)"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := walkWarning(root, filepath.Join(root, tc.rel), fs.ErrPermission)
			want := "Cannot inspect \"" + tc.want + "\": permission denied"
			if got != want {
				t.Fatalf("walkWarning() = %q, want %q", got, want)
			}
		})
	}
}
