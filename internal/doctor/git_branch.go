package doctor

import (
	"strings"
	"unicode"
	"unicode/utf8"
)

// parseGitHeadBranch extracts a symbolic branch reference without invoking git.
// A project's .git/HEAD is untrusted input: control, invisible formatting,
// and whitespace characters must never appear in terminal-facing findings.
func parseGitHeadBranch(data []byte) (string, bool) {
	if !utf8.Valid(data) {
		return "", false
	}
	value := strings.TrimSuffix(string(data), "\n")
	value = strings.TrimSuffix(value, "\r")
	const prefix = "ref: refs/heads/"
	if !strings.HasPrefix(value, prefix) {
		return "", false
	}
	branch := strings.TrimPrefix(value, prefix)
	if branch == "" || branch == "HEAD" || strings.Contains(branch, "\\") || strings.IndexFunc(branch, func(r rune) bool {
		return unicode.IsControl(r) || unicode.Is(unicode.Cf, r) || unicode.IsSpace(r)
	}) >= 0 {
		return "", false
	}
	// Enforce Git's refname constraints on the untrusted HEAD target. The
	// printable text alone is not enough: traversal-like components, @{, and
	// other reserved syntax must not be reported as legitimate branch names.
	if strings.HasPrefix(branch, "-") || strings.ContainsAny(branch, "~^:?*[") ||
		strings.Contains(branch, "..") || strings.Contains(branch, "@{") ||
		strings.HasSuffix(branch, ".") {
		return "", false
	}
	for _, component := range strings.Split(branch, "/") {
		if component == "" || strings.HasPrefix(component, ".") ||
			strings.HasSuffix(component, ".lock") {
			return "", false
		}
	}
	return branch, true
}
