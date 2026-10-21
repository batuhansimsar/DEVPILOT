package dockercheck

import (
	"context"
	"strings"
	"testing"
)

func TestValidDockerServerVersion(t *testing.T) {
	cases := []struct {
		version string
		valid   bool
	}{
		{"27.1.0", true},
		{"28.0.0+azure", true},
		{"25.0.0-rc.1", true},
		{"dev", true},
		{"", false},
		{"27.0.0\nFake=success", false},
		{"\x1b[2J27.0.0", false},
		{"27.1.0 token=secret", false},
		{"../../private", false},
		{"docker/28", false},
		{"二十八", false},
		{strings.Repeat("a", 129), false},
	}
	for _, tc := range cases {
		t.Run(tc.version, func(t *testing.T) {
			if got := validDockerServerVersion(tc.version); got != tc.valid {
				t.Errorf("validDockerServerVersion(%q) = %v, want %v", tc.version, got, tc.valid)
			}
		})
	}
}

func TestInspectRejectsUntrustedDockerVersion(t *testing.T) {
	const secret = "token=secret.private"
	for _, output := range []string{
		"27.0.0\n" + secret,
		"\x1b[2J27.0.0",
		strings.Repeat("x", 129),
		"",
	} {
		got := Inspect(context.Background(), func(context.Context, ...string) ([]byte, error) {
			return []byte(output), nil
		})
		if !got.Installed || got.Reachable || got.Version != "" ||
			got.Detail != "Docker returned invalid server version" ||
			strings.Contains(got.Detail, secret) {
			t.Errorf("Inspect should redact malformed Docker version: %+v", got)
		}
	}
}
