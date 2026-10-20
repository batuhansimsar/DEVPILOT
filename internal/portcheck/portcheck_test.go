package portcheck

import (
	"context"
	"encoding/json"
	"net"
	"strings"
	"testing"
	"time"
)

func TestCheckReachable(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	port := listener.Addr().(*net.TCPAddr).Port
	result, err := Check(context.Background(), "127.0.0.1", port, time.Second)
	if err != nil || !result.Reachable || result.Error != "" {
		t.Fatalf("result=%+v err=%v", result, err)
	}
	if result.Host != "127.0.0.1" || result.Port != port {
		t.Fatalf("unexpected endpoint: %+v", result)
	}
	assertLatencyJSON(t, result)
}

func TestCheckBracketedIPv6(t *testing.T) {
	listener, err := net.Listen("tcp6", "[::1]:0")
	if err != nil {
		t.Skipf("IPv6 loopback is unavailable: %v", err)
	}
	defer listener.Close()
	port := listener.Addr().(*net.TCPAddr).Port
	for _, host := range []string{"::1", "[::1]"} {
		t.Run(host, func(t *testing.T) {
			result, err := Check(context.Background(), host, port, time.Second)
			if err != nil || !result.Reachable || result.Host != host {
				t.Fatalf("result=%+v err=%v", result, err)
			}
		})
	}
}

func TestCheckUnreachable(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	listener.Close()
	result, err := Check(context.Background(), "127.0.0.1", port, time.Second)
	if err != nil || result.Reachable || result.Error == "" {
		t.Fatalf("result=%+v err=%v", result, err)
	}
	assertLatencyJSON(t, result)
}

func assertLatencyJSON(t *testing.T, result Result) {
	t.Helper()
	encoded, err := json.Marshal(result)
	if err != nil {
		t.Fatal(err)
	}
	var values map[string]any
	if err := json.Unmarshal(encoded, &values); err != nil {
		t.Fatal(err)
	}
	latency, ok := values["latency_ms"].(float64)
	if !ok || latency < 0 {
		t.Fatalf("missing or invalid latency in %s", encoded)
	}
}

func TestCheckRejectsInvalidArguments(t *testing.T) {
	cases := []struct {
		host    string
		port    int
		timeout time.Duration
	}{
		{"", 443, time.Second},
		{" example.org", 443, time.Second},
		{"example.org\n", 443, time.Second},
		{"bad host.example", 443, time.Second},
		{"bad\u00a0host.example", 443, time.Second},
		{"example.org/path", 443, time.Second},
		{"example.org:443", 443, time.Second},
		{"[::1", 443, time.Second},
		{"::1]", 443, time.Second},
		{"[example.org]", 443, time.Second},
		{"[127.0.0.1]", 443, time.Second},
		{"\x1b[31mexample.org", 443, time.Second},
		{"example.org", 0, time.Second},
		{"example.org", 65536, time.Second},
		{"example.org", 443, 0},
		{"example.org", 443, 31 * time.Second},
	}
	for _, tc := range cases {
		if _, err := Check(context.Background(), tc.host, tc.port, tc.timeout); err == nil {
			t.Errorf("expected error for host=%q port=%d timeout=%s", tc.host, tc.port, tc.timeout)
		}
	}
}

func TestCheckHonorsCanceledContext(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	result, err := Check(ctx, "127.0.0.1", 12345, time.Second)
	if err != nil || result.Reachable || !strings.Contains(result.Error, "canceled") {
		t.Fatalf("result=%+v err=%v", result, err)
	}
	assertLatencyJSON(t, result)
}

// Reject Unicode formatting codepoints before performing any network I/O;
// these characters can visually spoof endpoint hostnames in CLI output.
func TestCheckRejectsInvisibleUnicodeFormatting(t *testing.T) {
	cases := []struct {
		name string
		host string
	}{
		{"rtl-override", "example\u202e.org"},
		{"ltr-isolate", "example\u2066.org"},
		{"zero-width-space", "example\u200b.org"},
		{"soft-hyphen", "example\u00ad.org"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			result, err := Check(context.Background(), tc.host, 443, time.Second)
			if err == nil || result != (Result{}) {
				t.Fatalf("invisible formatting character accepted: result=%+v err=%v", result, err)
			}
		})
	}
}
