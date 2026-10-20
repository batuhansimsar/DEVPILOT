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
