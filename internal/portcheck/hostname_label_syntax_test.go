package portcheck

import (
	"context"
	"strings"
	"testing"
	"time"
)

func TestCheckRejectsInvalidDNSLabelSyntax(t *testing.T) {
	invalid := []string{
		"bad_name.example", "-bad.example", "bad-.example",
		"bad+name.example", "bad!name.example", "bad=name.example",
		"bad~name.example", "bad,name.example", "bad|name.example",
		"bad🙂.example", "example。org", "\xff.example",
	}
	for _, host := range invalid {
		t.Run(host, func(t *testing.T) {
			got, err := Check(context.Background(), host, 443, time.Second)
			if err == nil || got != (Result{}) {
				t.Fatalf("invalid hostname accepted: result=%+v err=%v", got, err)
			}
			if strings.Contains(err.Error(), host) {
				t.Fatal("hostname leaked into validation error")
			}
		})
	}
}

func TestCheckAcceptsValidDNSLabelSyntax(t *testing.T) {
	valid := []string{
		"example.org", "example.org.", "localhost", "127.0.0.1",
		"a-b.example", "xn--bcher-kva.example", "bücher.example",
		"e\u0301.example",
	}
	for _, host := range valid {
		t.Run(host, func(t *testing.T) {
			ctx, cancel := context.WithCancel(context.Background())
			cancel() // Validation runs but no DNS or TCP traffic is generated.
			got, err := Check(ctx, host, 443, time.Second)
			if err != nil || got.Host != host {
				t.Fatalf("valid hostname rejected: result=%+v err=%v", got, err)
			}
		})
	}
}
