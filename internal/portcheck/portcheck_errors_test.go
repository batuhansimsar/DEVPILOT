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

func TestSafeDialErrorRedactsNetworkDetails(t *testing.T) {
	const sensitive = "private.internal.example:8443"
	cases := []struct {
		name string
		err  error
		want string
	}{
		{"canceled", fmt.Errorf("%s: %w", sensitive, context.Canceled), "connection canceled"},
		{"deadline", fmt.Errorf("%s: %w", sensitive, context.DeadlineExceeded), "connection timed out"},
		{"timeout", &net.DNSError{Err: sensitive, IsTimeout: true}, "connection timed out"},
		{"refused", fmt.Errorf("%s: %w", sensitive, syscall.ECONNREFUSED), "connection refused"},
		{"unreachable", fmt.Errorf("%s: %w", sensitive, syscall.ENETUNREACH), "network unreachable"},
		{"host unreachable", fmt.Errorf("%s: %w", sensitive, syscall.EHOSTUNREACH), "host unreachable"},
		{"dns", &net.DNSError{Err: sensitive, Name: sensitive}, "DNS resolution failed"},
		{"other", errors.New(sensitive), "TCP connection failed"},
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

func TestCheckCanceledConnectionReturnsSafeError(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	got, err := Check(ctx, "127.0.0.1", 443, time.Second)
	if err != nil || got.Reachable || got.Error != "connection canceled" {
		t.Fatalf("result=%+v err=%v", got, err)
	}
}

func TestCheckRefusedConnectionDoesNotExposeRawDialError(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	if err := listener.Close(); err != nil {
		t.Fatal(err)
	}
	got, err := Check(context.Background(), "127.0.0.1", port, time.Second)
	if err != nil || got.Reachable || got.Error != "connection refused" {
		t.Fatalf("result=%+v err=%v", got, err)
	}
}
