package dockercheck

import (
	"context"
	"errors"
	"strings"
	"testing"
)

type errorWithSideEffect struct{}

func (errorWithSideEffect) Error() string { panic("untrusted Error method was invoked") }

func TestAlternateDockerCLIErrorsDoNotLeakDetails(t *testing.T) {
	const secret = "token=private-registry-password\x1b[31m"
	for _, tc := range []struct {
		name string
		err  error
	}{
		{"sensitive error", errors.New("docker daemon returned " + secret)},
		{"panicking error", errorWithSideEffect{}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			run := func(context.Context, ...string) ([]byte, error) { return nil, tc.err }
			daemon := Inspect(context.Background(), run)
			containers := List(context.Background(), run)
			for _, detail := range []string{daemon.Detail, containers.Detail} {
				if detail != "Docker command failed; check Docker CLI and daemon access" || strings.Contains(detail, secret) {
					t.Fatalf("unsafe diagnostic: %q", detail)
				}
			}
			if !daemon.Installed || daemon.Reachable || containers.Available || len(containers.Items) != 0 {
				t.Fatalf("failed runner reported healthy: daemon=%+v containers=%+v", daemon, containers)
			}
		})
	}
}
