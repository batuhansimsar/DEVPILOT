package portcheck

import (
	"context"
	"strings"
	"testing"
	"time"
)

func TestCheckRejectsAmbiguousNumericHosts(t *testing.T) {
	for _, host := range []string{"127.1", "127.000.000.001", "999.999.999.999", "1.2.3", "1.2.3.4.5", "127.0.0.1.."} {
		t.Run(host, func(t *testing.T) {
			result, err := Check(context.Background(), host, 443, time.Second)
			if err == nil || result != (Result{}) {
				t.Fatalf("ambiguous numeric hostname accepted: err=%v result=%+v", err, result)
			}
			if strings.Contains(err.Error(), host) {
				t.Fatal("validation error exposed the supplied hostname")
			}
		})
	}
}

func TestCheckPreservesCanonicalIPv4AndDNS(t *testing.T) {
	for _, host := range []string{"127.0.0.1", "127.0.0.1.", "example.org", "api.123", "bücher.example"} {
		t.Run(host, func(t *testing.T) {
			ctx, cancel := context.WithCancel(context.Background())
			cancel() // Exercise validation without making a network request.
			result, err := Check(ctx, host, 443, time.Second)
			if err != nil || result.Host != host {
				t.Fatalf("valid hostname rejected: err=%v result=%+v", err, result)
			}
		})
	}
}
