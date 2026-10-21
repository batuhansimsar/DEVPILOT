package portcheck

import (
	"context"
	"strings"
	"testing"
	"time"
)

func TestCheckRejectsInvalidDNSNameLengthsBeforeDial(t *testing.T) {
	tooLongName := strings.Repeat("a", 63) + "." + strings.Repeat("b", 63) + "." + strings.Repeat("c", 63) + "." + strings.Repeat("d", 62)
	cases := []string{
		strings.Repeat("a", 64) + ".test",
		"example..org",
		".example.org",
		".",
		"example.org..",
		tooLongName,
		tooLongName + ".",
		strings.Repeat("a", 8192),
	}
	for _, host := range cases {
		t.Run(host[:min(len(host), 32)], func(t *testing.T) {
			result, err := Check(context.Background(), host, 443, time.Second)
			if err == nil || result != (Result{}) {
				t.Fatalf("invalid DNS hostname accepted: err=%v result=%+v", err, result)
			}
			if strings.Contains(err.Error(), host) {
				t.Fatalf("error message leaked input hostname")
			}
		})
	}
}

func TestCheckAllowsBoundaryDNSNamesAndIPAddresses(t *testing.T) {
	maxName := strings.Repeat("a", 63) + "." + strings.Repeat("b", 63) + "." + strings.Repeat("c", 63) + "." + strings.Repeat("d", 61)
	if len(maxName) != 253 {
		t.Fatal("test setup must produce a 253-byte DNS name")
	}
	for _, host := range []string{maxName, maxName + ".", "localhost", "127.0.0.1", "[::1]", "::1"} {
		t.Run(host[:min(len(host), 32)], func(t *testing.T) {
			ctx, cancel := context.WithCancel(context.Background())
			cancel() // Never perform real DNS/network access for the boundary test.
			result, err := Check(ctx, host, 443, time.Second)
			if err != nil || result.Host != host {
				t.Fatalf("valid hostname rejected: err=%v result=%+v", err, result)
			}
		})
	}
}
