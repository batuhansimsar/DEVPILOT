package dockercheck

import (
	"context"
	"strings"
	"testing"
)

// The optional Docker integration must explain a missing executable instead
// of returning an empty "Docker command failed:" diagnostic.
func TestSystemCLIReportsMissingDockerExecutable(t *testing.T) {
	t.Setenv("PATH", t.TempDir())

	output, err := SystemCLI(context.Background(), "info")
	if err == nil || string(output) != "" || !strings.Contains(err.Error(), "Docker CLI not found on PATH") {
		t.Fatalf("SystemCLI with missing docker = %q, %v", output, err)
	}

	containers := List(context.Background(), nil)
	if containers.Available || containers.Items == nil || len(containers.Items) != 0 || !strings.Contains(containers.Detail, "Docker CLI not found on PATH") {
		t.Fatalf("List with missing docker = %+v", containers)
	}
}
