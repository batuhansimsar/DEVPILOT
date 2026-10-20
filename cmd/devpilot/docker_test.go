package main

import (
	"bytes"
	"context"
	"strings"
	"testing"
)

func TestDockerRejectsUnexpectedArguments(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := run(context.Background(), []string{"docker", "--json", "rm"}, &stdout, &stderr)
	if code != 2 || !strings.Contains(stderr.String(), "optional ps") {
		t.Fatalf("code=%d stderr=%q", code, stderr.String())
	}
}

func TestDockerUsageIsDiscoverable(t *testing.T) {
	var stdout bytes.Buffer
	usage(&stdout)
	if !strings.Contains(stdout.String(), "devpilot docker [--json] [ps]") {
		t.Fatalf("usage omitted Docker command: %q", stdout.String())
	}
}
