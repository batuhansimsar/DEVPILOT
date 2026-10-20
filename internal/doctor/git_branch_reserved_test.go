package doctor

import "testing"

// Git's --branch validation reserves HEAD even though it is otherwise a
// syntactically valid ref component. HEAD is not a real branch name.
func TestParseGitHeadBranchRejectsReservedHEAD(t *testing.T) {
	got, ok := parseGitHeadBranch([]byte("ref: refs/heads/HEAD\n"))
	if ok || got != "" {
		t.Fatalf("reserved HEAD must not be reported as a branch: %q, %v", got, ok)
	}
}

func TestParseGitHeadBranchPreservesNonReservedHeadNames(t *testing.T) {
	for _, name := range []string{"head", "Head", "HEAD/fix", "feature/HEAD", "FETCH_HEAD"} {
		t.Run(name, func(t *testing.T) {
			got, ok := parseGitHeadBranch([]byte("ref: refs/heads/" + name + "\n"))
			if !ok || got != name {
				t.Fatalf("valid branch %q was rejected: got %q, ok %v", name, got, ok)
			}
		})
	}
}
