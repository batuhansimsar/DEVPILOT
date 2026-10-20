package dockercheck

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"strings"
	"testing"
)

func TestInspectDaemon(t *testing.T) {
	call := func(_ context.Context, args ...string) ([]byte, error) {
		if strings.Join(args, " ") != "info --format {{.ServerVersion}}" {
			t.Fatalf("unexpected arguments: %v", args)
		}
		return []byte("27.1.0\n"), nil
	}
	got := Inspect(context.Background(), call)
	if !got.Installed || !got.Reachable || got.Version != "27.1.0" {
		t.Fatalf("bad daemon status: %+v", got)
	}
}

func TestOfflineDaemon(t *testing.T) {
	got := Inspect(context.Background(), func(_ context.Context, _ ...string) ([]byte, error) {
		return nil, errors.New("daemon is stopped")
	})
	if got.Reachable || !got.Installed || !strings.Contains(got.Detail, "stopped") {
		t.Fatalf("expected offline status: %+v", got)
	}
}

func TestListParsesJSONL(t *testing.T) {
	got := List(context.Background(), func(_ context.Context, args ...string) ([]byte, error) {
		if strings.Join(args, " ") != "ps --format {{json .}}" {
			t.Fatalf("unexpected arguments: %v", args)
		}
		return []byte("{\"Names\":\"web\"}\n{\"Names\":\"db\"}\n"), nil
	})
	if !got.Available || len(got.Items) != 2 {
		t.Fatalf("unexpected result: %+v", got)
	}
	var first struct{ Names string }
	if err := json.Unmarshal(got.Items[0], &first); err != nil || first.Names != "web" {
		t.Fatalf("first container: %v %+v", err, first)
	}
}

func TestListBadJSON(t *testing.T) {
	got := List(context.Background(), func(_ context.Context, _ ...string) ([]byte, error) {
		return []byte("private unexpected data"), nil
	})
	if got.Available || len(got.Items) != 0 {
		t.Fatalf("unexpected result: %+v", got)
	}
}

func TestListEmpty(t *testing.T) {
	got := List(context.Background(), func(_ context.Context, _ ...string) ([]byte, error) {
		return []byte(""), nil
	})
	if !got.Available || len(got.Items) != 0 {
		t.Fatalf("unexpected result: %+v", got)
	}
}

func TestBoundedWriterRejectsOversizedOutput(t *testing.T) {
	var buf bytes.Buffer
	writer := &boundedWriter{remaining: 3, dest: &buf}
	if _, err := writer.Write([]byte("abcd")); !errors.Is(err, errLimit) {
		t.Fatalf("expected limit error, got %v", err)
	}
	if buf.String() != "abc" {
		t.Fatalf("unexpected contents: %s", buf.String())
	}
}

// JSON whitespace is legal, and the Docker CLI may use CRLF line endings.
// A malformed line must still invalidate the complete result.
func TestListWhitespaceAndInvalidLines(t *testing.T) {
	cases := []struct {
		name      string
		output    string
		wantNames []string
		valid     bool
	}{
		{"indented CRLF", "  {\"Names\":\"web\"}\r\n\t{\"Names\":\"db\"} \r\n", []string{"web", "db"}, true},
		{"blank lines", " \n\t\n {\"Names\":\"web\"} \n", []string{"web"}, true},
		{"invalid after valid", " {\"Names\":\"web\"}\n not-json\n", nil, false},
		{"array disallowed", " [{\"Names\":\"web\"}]\n", nil, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := List(context.Background(), func(context.Context, ...string) ([]byte, error) {
				return []byte(tc.output), nil
			})
			if got.Available != tc.valid || len(got.Items) != len(tc.wantNames) {
				t.Fatalf("Available=%v Items=%d Detail=%q", got.Available, len(got.Items), got.Detail)
			}
			for i, raw := range got.Items {
				var item struct{ Names string }
				if err := json.Unmarshal(raw, &item); err != nil || item.Names != tc.wantNames[i] {
					t.Fatalf("item %d = %s err %v", i, raw, err)
				}
			}
		})
	}
}
