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

func TestSafeDialErrorAdditionalCategories(t *testing.T) {
	const sensitive = "private.internal.example:8443"
	cases := []struct {
		name string
		err  error
		want string
	}{
		{"connection reset", fmt.Errorf("%s: %w", sensitive, syscall.ECONNRESET), "connection reset"},
		{"connection aborted", fmt.Errorf("%s: %w", sensitive, syscall.ECONNABORTED), "connection aborted"},
		{"unavailable local address", fmt.Errorf("%s: %w", sensitive, syscall.EADDRNOTAVAIL), "local address unavailable"},
		{"DNS missing", &net.DNSError{Err: sensitive, Name: sensitive, IsNotFound: true}, "DNS name not found"},
		{"DNS generic", &net.DNSError{Err: sensitive, Name: sensitive}, "DNS resolution failed"},
		{"refused", fmt.Errorf("%s: %w", sensitive, syscall.ECONNREFUSED), "connection refused"},
		{"timeout precedence", fmt.Errorf("%w: %w", context.DeadlineExceeded, syscall.ECONNRESET), "connection timed out"},
		{"other", errors.New(sensitive), "TCP connection failed"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := safeDialError(tc.err)
			if got != tc.want || strings.Contains(got, sensitive) {
				t.Fatalf("got=%q want=%q", got, tc.want)
			}
		})
	}
}

func TestCheckRealLocalProbe(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	p := listener.Addr().(*net.TCPAddr).Port
	result, err := Check(context.Background(), "127.0.0.1", p, time.Second)
	if err != nil || !result.Reachable || result.Error != "" {
		t.Fatalf("result=%+v err=%v", result, err)
	}
}
