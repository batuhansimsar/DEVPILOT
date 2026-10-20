package doctor

import "testing"

// HEAD files are untrusted text and must follow Git refname syntax, not merely
// have printable characters. These cases must not become CLI branch findings.
func TestParseGitHeadBranchRejectsInvalidRefnames(t *testing.T) {
	invalid := []string{
		"../outside", "feature/../outside", "a//b", "/main", "main/",
		".hidden", "feature/.hidden", "fix.lock", "feature/stale.lock",
		"feature..bad", "trailing.", "ends/.", "-option", "main~1",
		"main^2", "topic:alt", "feature?", "feature*", "branch[1]",
		"feature@{1}",
	}
	for _, branch := range invalid {
		t.Run(branch, func(t *testing.T) {
			if got, ok := parseGitHeadBranch([]byte("ref: refs/heads/" + branch + "\n")); ok || got != "" {
				t.Fatalf("invalid refname %q accepted as %q", branch, got)
			}
		})
	}
}

func TestParseGitHeadBranchAllowsLegitimatePrintableRefnames(t *testing.T) {
	for _, branch := range []string{"feature/auth", "release/v2.0", "topic+one", "fix/日本語"} {
		t.Run(branch, func(t *testing.T) {
			got, ok := parseGitHeadBranch([]byte("ref: refs/heads/" + branch + "\n"))
			if !ok || got != branch {
				t.Fatalf("valid refname %q rejected", branch)
			}
		})
	}
}
