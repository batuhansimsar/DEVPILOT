package main

import (
	"context"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
)

func TestFilterTestEnvironment(t *testing.T) {
	original := []string{
		"PATH=/usr/bin", "GH_TOKEN=x", "GITHUB_TOKEN=x", "AWS_SECRET_ACCESS_KEY=x",
		"DATABASE_PASSWORD=x", "CUSTOM_API_KEY=x", "AZURE_CLIENT_SECRET=x",
		"AUTHORIZATION_BEARER=x", "HOME=/home/dev", "DISPLAY=:0",
	}
	got := filteredTestEnvironment(original)
	want := []string{"PATH=/usr/bin", "HOME=/home/dev", "DISPLAY=:0"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %v, want %v", got, want)
	}
	if len(original) != 10 {
		t.Fatal("mutated original environment")
	}
}

func TestTrustedCommandHasFinitePipeWaitAndWorkspace(t *testing.T) {
	dir := t.TempDir()
	cmd := newTrustedTestCommand(context.Background(), dir, "go", "version")
	if cmd.Dir != dir || cmd.WaitDelay != 2*time.Second {
		t.Fatalf("command not hardened: %+v", cmd)
	}
	if !reflect.DeepEqual(cmd.Args, []string{"go", "version"}) {
		t.Fatalf("unexpected exec args: %v", cmd.Args)
	}
	if cmd.Env == nil {
		t.Fatal("nil environment would inherit all credentials")
	}
}

func TestSensitiveEnvNotInheritedByChild(t *testing.T) {
	t.Setenv("DEVPILOT_PROBE_SECRET", "do-not-pass-to-tests")
	script := filepath.Join(t.TempDir(), "check.go")
	src := "package main\nimport \"os\"\nfunc main() { if os.Getenv(\"DEVPILOT_PROBE_SECRET\") != \"\" { os.Exit(42) } }\n"
	if err := os.WriteFile(script, []byte(src), 0600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	cmd := newTrustedTestCommand(ctx, filepath.Dir(script), "go", "run", script)
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("child inherited secret or failed: %v\n%s", err, strings.TrimSpace(string(output)))
	}
}
