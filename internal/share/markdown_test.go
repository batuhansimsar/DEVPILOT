package share

import (
	"bytes"
	"errors"
	"strings"
	"testing"
)

func TestMarkdownOmitsPathsAndSensitiveEnvironmentNames(t *testing.T) {
	workspace := "/home/alice/private-company/top-secret"
	s := Snapshot{Workspace: workspace, Languages: []string{"Go"}, Frameworks: []string{"React"}, PackageManager: "npm", TestCommand: "go test ./...", Findings: []Finding{
		{Level: "warning", Code: "package-json-unreadable", Message: "cannot inspect " + workspace + "/package.json | invalid", Remedy: "Review " + workspace + "/package.json"},
		{Level: "info", Code: "env-local-missing-keys", Message: "Missing PRIVATE_API_KEY and PAYMENT_TOKEN", Remedy: "Review private variables"},
		{Level: "info", Code: "git-branch", Message: "Git branch: customer-name/secret-release"},
	}}
	var out bytes.Buffer
	if err := Markdown(&out, s); err != nil {
		t.Fatal(err)
	}
	result := out.String()
	for _, bad := range []string{workspace, "PRIVATE_API_KEY", "PAYMENT_TOKEN", "customer-name/secret-release"} {
		if strings.Contains(result, bad) {
			t.Fatalf("private information disclosed: %q", bad)
		}
	}
	for _, want := range []string{"# DevPilot diagnostic snapshot", "Go", "React", "go test ./...", "[workspace]/package.json", "\\|", "env-local-missing-keys", "Review before sharing"} {
		if !strings.Contains(result, want) {
			t.Errorf("missing %q in report:\n%s", want, result)
		}
	}
}

func TestMarkdownEmptyInputAndNoFindings(t *testing.T) {
	var b bytes.Buffer
	if err := Markdown(&b, Snapshot{}); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(b.String(), "No shareable findings") || !strings.Contains(b.String(), "Not detected") {
		t.Fatal(b.String())
	}
}

type failedWriter struct{}

func (failedWriter) Write([]byte) (int, error) { return 0, errors.New("write error") }
func TestMarkdownPropagatesWriteErrors(t *testing.T) {
	if err := Markdown(failedWriter{}, Snapshot{}); err == nil {
		t.Fatal("write failure swallowed")
	}
}
