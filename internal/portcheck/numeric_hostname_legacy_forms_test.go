package portcheck

import (
	"context"
	"strings"
	"testing"
	"time"
)

func TestCheckRejectsLegacyNumericIPAliases(t *testing.T) {
	for _, host := range []string{
		"2130706433", "127", "0177", "0x7f000001",
		"0X7F000001", "0x7f.0.0.1", "0X7F.1", "127.0x0.0.1",
		"0177.1", "127.1", "127.0.0.01",
	} {
		t.Run(host, func(t *testing.T) {
			result, err := Check(context.Background(), host, 443, time.Second)
			if err == nil || result != (Result{}) {
				t.Fatalf("unsafe numeric alias passed validation: result=%+v err=%v", result, err)
			}
			if strings.Contains(err.Error(), host) {
				t.Fatalf("validation error contains untrusted host: %v", err)
			}
		})
	}
}

func TestCheckAllowsDNSNamesWithNumbers(t *testing.T) {
	for _, host := range []string{
		"api123", "api.123", "127.example", "0xnothex", "127.0.0.1", "127.0.0.1.",
	} {
		t.Run(host, func(t *testing.T) {
			ctx, cancel := context.WithCancel(context.Background())
			cancel() // Run validation without contacting the network.
			result, err := Check(ctx, host, 443, time.Second)
			if err != nil || result.Host != host {
				t.Fatalf("safe host rejected: result=%+v err=%v", result, err)
			}
		})
	}
}
