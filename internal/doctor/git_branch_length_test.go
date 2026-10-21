package doctor

import (
	"strings"
	"testing"
)

func TestParseGitHeadBranchBoundsDisplayedName(t *testing.T) {
	prefix := "ref: refs/heads/"
	longest := strings.Repeat("topic/", 170) + "abcd" // 1024 bytes
	if len(longest) != maxGitBranchNameBytes {
		t.Fatalf("test setup: got %d bytes", len(longest))
	}
	got, ok := parseGitHeadBranch([]byte(prefix + longest + "\r\n"))
	if !ok || got != longest {
		t.Fatalf("maximum permitted branch rejected: length=%d ok=%v", len(got), ok)
	}
	for name, branch := range map[string]string{
		"one byte too long": longest + "e",
		"megabyte long":     strings.Repeat("x", 1<<20),
	} {
		t.Run(name, func(t *testing.T) {
			got, ok := parseGitHeadBranch([]byte(prefix + branch + "\n"))
			if ok || got != "" {
				t.Fatalf("oversized branch reported: length=%d", len(got))
			}
		})
	}
}

func TestParseGitHeadBranchRejectsOversizedUTF8Input(t *testing.T) {
	branch := strings.Repeat("界", 342) // 1026 UTF-8 bytes
	if got, ok := parseGitHeadBranch([]byte("ref: refs/heads/" + branch + "\n")); ok || got != "" {
		t.Fatalf("oversized Unicode branch reported: length=%d", len(got))
	}
}
