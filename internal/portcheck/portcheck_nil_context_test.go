package portcheck

import (
	"strings"
	"testing"
	"time"
)

func TestCheckRejectsNilContextWithoutPanic(t *testing.T) {
	result, err := Check(nil, "127.0.0.1", 443, time.Second)
	if err == nil || !strings.Contains(err.Error(), "context") {
		t.Fatalf("expected a context validation error, got result=%+v err=%v", result, err)
	}
	if result != (Result{}) {
		t.Fatalf("invalid context should not initiate a probe: %+v", result)
	}
}
