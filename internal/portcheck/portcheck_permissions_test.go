package portcheck

import (
	"context"
	"fmt"
	"net"
	"strings"
	"syscall"
	"testing"
)

func TestSafeDialErrorPermissionDiagnostics(t *testing.T) {
	const sensitive = "private.internal.example:8443"
	cases := []struct {
		name string
		err  error
		want string
	}{
		{"access denied", fmt.Errorf("%s: %w", sensitive, syscall.EACCES), "connection blocked by local permissions"},
		{"operation not permitted", &net.OpError{Op: "dial", Net: "tcp", Err: fmt.Errorf("%s: %w", sensitive, syscall.EPERM)}, "connection blocked by local permissions"},
		{"deadline takes precedence", fmt.Errorf("%w: %w", context.DeadlineExceeded, syscall.EACCES), "connection timed out"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := safeDialError(tc.err)
			if got != tc.want || strings.Contains(got, sensitive) {
				t.Fatalf("safeDialError() = %q, want %q", got, tc.want)
			}
		})
	}
}
