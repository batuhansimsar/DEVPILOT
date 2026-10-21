package dockercheck

import (
	"context"
	"strings"
	"testing"
)

func TestInspectRejectsOversizedAlternateRunnerOutput(t *testing.T) {
	output := []byte(strings.Repeat("v", maxOutput+1))
	result := Inspect(context.Background(), func(context.Context, ...string) ([]byte, error) {
		return output, nil
	})
	if !result.Installed || result.Reachable || result.Version != "" || result.Detail != "Docker returned oversized server version" {
		t.Fatalf("oversized daemon response was not rejected safely: %+v", result)
	}
}

func TestListRejectsOversizedAlternateRunnerOutput(t *testing.T) {
	output := []byte(`{"Names":"` + strings.Repeat("x", maxOutput) + `"}`)
	result := List(context.Background(), func(context.Context, ...string) ([]byte, error) {
		return output, nil
	})
	if result.Available || len(result.Items) != 0 || result.Detail != "Docker returned oversized container metadata" {
		t.Fatalf("oversized container response was not rejected safely: %+v", result)
	}
}

func TestListAlternateRunnerAtLimit(t *testing.T) {
	output := []byte(`{"Names":"` + strings.Repeat("x", maxOutput-len(`{"Names":""}`)) + `"}`)
	if len(output) != maxOutput {
		t.Fatalf("invalid fixture size: %d", len(output))
	}
	result := List(context.Background(), func(context.Context, ...string) ([]byte, error) {
		return output, nil
	})
	if !result.Available || len(result.Items) != 1 {
		t.Fatalf("valid response at byte limit was rejected: %+v", result)
	}
}
