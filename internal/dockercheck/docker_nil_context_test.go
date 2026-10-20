package dockercheck

import (
	"context"
	"strings"
	"testing"
)

// Invalid contexts should never panic or launch a Docker command.
func TestNilContextRejectedWithoutExecutingDocker(t *testing.T) {
	output, err := SystemCLI(nil, "info")
	if err == nil || !strings.Contains(err.Error(), "context must not be nil") || output != nil {
		t.Fatalf("SystemCLI(nil) = %q, %v; want a context error and no output", output, err)
	}

	called := false
	run := func(_ context.Context, _ ...string) ([]byte, error) {
		called = true
		return []byte("unexpected"), nil
	}

	daemon := Inspect(nil, run)
	if called || daemon.Installed || daemon.Reachable || !strings.Contains(daemon.Detail, "context must not be nil") {
		t.Fatalf("Inspect(nil) = %+v, runner called=%v", daemon, called)
	}

	containers := List(nil, run)
	if called || containers.Available || containers.Items == nil || len(containers.Items) != 0 || !strings.Contains(containers.Detail, "context must not be nil") {
		t.Fatalf("List(nil) = %+v, runner called=%v", containers, called)
	}

	// The nil-runner paths must also reject the context before looking up or
	// attempting to execute the Docker CLI.
	if got := Inspect(nil, nil); got.Detail != "context must not be nil" {
		t.Fatalf("Inspect(nil, nil) = %+v", got)
	}
	if got := List(nil, nil); got.Detail != "context must not be nil" {
		t.Fatalf("List(nil, nil) = %+v", got)
	}
}
