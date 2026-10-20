package portcheck

import (
	"context"
	"errors"
	"fmt"
	"net"
	"strings"
	"syscall"
	"testing"
	"time"
)

func TestSafeDialErrorCategoriesAndRedaction(t *testing.T) {
	cases := []struct {
		name string
		err  error
		want string
	}{
		{"canceled", fmt.Errorf("secret.internal: %w", context.Canceled), "connection canceled"},
		{"deadline", fmt.Errorf("secret.internal: %w", context.DeadlineExceeded), "connection timed out"},
		{"dns", &net.DNSError{Err: "secret resolver details", Name: "secret.internal"}, "DNS resolution failed"},
		{"refused", &net.OpError{Op: "dial", Net: "tcp", Addr: &net.TCPAddr{IP: net.ParseIP("192.0.2.17"), Port: 443}, Err: syscall.ECONNREFUSED}, "connection refused"},
		{"network", fmt.Errorf("secret.internal: %w", syscall.ENETUNREACH), "network unreachable"},
		{"host", fmt.Errorf("secret.internal: %w", syscall.EHOSTUNREACH), "host unreachable"},
		{"unknown", errors.New("secret.internal: password=hidden"), "TCP connection failed"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := safeDialError(tc.err)
			if got != tc.want {
				t.Fatalf("safeDialError() = %q, want %q", got, tc.want)
			}
			if strings.Contains(got, "secret") || strings.Contains(got, "192.0.2.17") || strings.Contains(got, "hidden") {
				t.Fatalf("sensitive details leaked: %q", got)
			}
		})
	}
}

// The live Check path must use the sanitized diagnostic rather than returning
// the full net.OpError, which embeds the host and port.
func TestCheckHidesDialTargetInError(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	listener.Close()

	result, err := Check(context.Background(), "127.0.0.1", port, time.Second)
	if err != nil {
		t.Fatalf("Check returned error: %v", err)
	}
	if result.Reachable {
		t.Skip("port was reallocated before the probe")
	}
	if result.Error != "connection refused" {
		t.Fatalf("unexpected sanitized error %q", result.Error)
	}
	if strings.Contains(result.Error, "127.0.0.1") {
		t.Fatalf("dial target leaked: %s", result.Error)
	}
}
