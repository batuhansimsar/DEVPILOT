package doctor

import (
	"strings"
	"testing"
)

func TestIsGitDetachedHead(t *testing.T) {
	tests := []struct {
		name  string
		head  string
		valid bool
	}{
		{"sha1", strings.Repeat("a1", 20) + "\n", true},
		{"sha256", strings.Repeat("Ab02", 16) + "\r\n", true},
		{"sha1 no newline", strings.Repeat("0", 40), true},
		{"symbolic branch", "ref: refs/heads/main\n", false},
		{"non hex 40 chars", strings.Repeat("z", 40) + "\n", false},
		{"non hex 64 chars", strings.Repeat("g", 64) + "\n", false},
		{"short hash", strings.Repeat("f", 39) + "\n", false},
		{"surrounding whitespace", " " + strings.Repeat("f", 40) + "\n", false},
		{"extra newline", strings.Repeat("f", 40) + "\n\n", false},
		{"embedded newline", strings.Repeat("f", 20) + "\n" + strings.Repeat("f", 20), false},
		{"control byte", strings.Repeat("f", 39) + "\x1b", false},
		{"empty", "", false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := isGitDetachedHead([]byte(tt.head))
			if got != tt.valid {
				t.Fatalf("isGitDetachedHead(%q) = %t, want %t", tt.head, got, tt.valid)
			}
		})
	}
}
