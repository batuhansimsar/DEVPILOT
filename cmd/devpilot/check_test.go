package main

import (
	"bytes"
	"context"
	"encoding/json"
	"net"
	"strconv"
	"strings"
	"testing"
)

func TestCheckCLIJSON(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	port := listener.Addr().(*net.TCPAddr).Port
	var stdout, stderr bytes.Buffer
	code := run(context.Background(), []string{"check", "--json", "--timeout=1s", "127.0.0.1", strconv.Itoa(port)}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("exit %d: %s", code, stderr.String())
	}
	var result struct {
		Host      string   `json:"host"`
		Port      int      `json:"port"`
		Reachable bool     `json:"reachable"`
		LatencyMS *float64 `json:"latency_ms"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result.Host != "127.0.0.1" || result.Port != port || !result.Reachable || result.LatencyMS == nil || *result.LatencyMS < 0 {
		t.Fatalf("unexpected result: %+v", result)
	}
}

func TestCheckCLIInvalidArgs(t *testing.T) {
	cases := [][]string{
		{"check"},
		{"check", "example.org", "not-a-port"},
		{"check", "example.org", "65536"},
		{"check", "--timeout=0", "example.org", "443"},
		{"check", "--timeout=31s", "example.org", "443"},
	}
	for _, args := range cases {
		var stdout, stderr bytes.Buffer
		if code := run(context.Background(), args, &stdout, &stderr); code != 2 {
			t.Errorf("args=%v, exit=%d, stderr=%s", args, code, stderr.String())
		}
	}
}

func TestCheckCLIUnreachable(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	listener.Close()
	var stdout, stderr bytes.Buffer
	code := run(context.Background(), []string{"check", "--timeout=1s", "127.0.0.1", strconv.Itoa(port)}, &stdout, &stderr)
	if code != 1 || !strings.Contains(stdout.String(), "unreachable") || !strings.Contains(stdout.String(), " ms)") {
		t.Fatalf("exit=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
}
