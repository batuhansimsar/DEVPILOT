package outputguard

import (
	"bytes"
	"strings"
	"testing"
)

func TestBoundedOutput(t *testing.T) {
	b := &Buffer{}
	input := []byte(strings.Repeat("x", Limit+200))
	n, err := b.Write(input)
	if err != nil || n != len(input) {
		t.Fatalf("Write: n=%d err=%v", n, err)
	}
	if _, err := b.Write([]byte("more")); err != nil {
		t.Fatal(err)
	}
	var output bytes.Buffer
	if err := b.Flush(&output); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(output.String(), "output truncated") {
		t.Fatal("missing truncation notice")
	}
	if len(output.String()) > Limit+128 {
		t.Fatal("unbounded output")
	}
}

func TestRedactionAndPlainOutput(t *testing.T) {
	t.Setenv("DEVPILOT_TEST_SECRET", "very-sensitive-123")
	input := "hello\nMY_API_TOKEN=abc123456\nPASSWORD: supersecret\nghp_abcdefghijklmnopqrstuvwxyz0123456789\nvery-sensitive-123\n"
	result := Redact(input)
	for _, secret := range []string{"abc123456", "supersecret", "ghp_abcdefghijklmnopqrstuvwxyz0123456789", "very-sensitive-123"} {
		if strings.Contains(result, secret) {
			t.Errorf("failed to redact %s", secret)
		}
	}
	if !strings.Contains(result, "hello") {
		t.Fatal("ordinary output lost")
	}
}

func TestFlushPreservesCleanOutput(t *testing.T) {
	b := &Buffer{}
	_, _ = b.Write([]byte("passed\n"))
	var out bytes.Buffer
	if err := b.Flush(&out); err != nil {
		t.Fatal(err)
	}
	if out.String() != "passed\n" {
		t.Fatalf("unexpected %q", out.String())
	}
}
