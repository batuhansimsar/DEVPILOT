package portcheck

import (
	"context"
	"strings"
	"testing"
	"time"
)

func TestCheckRejectsLeadingUnicodeCombiningMark(t *testing.T) {
	for _, host := range []string{
		"\u0301example.test", // Combining acute accent before the first letter.
		"example.\u034fhost", // Combining grapheme joiner at a label boundary.
		"\u093ehost.example", // Combining spacing mark.
	} {
		result, err := Check(context.Background(), host, 443, time.Second)
		if err == nil || result != (Result{}) {
			t.Errorf("leading Unicode mark accepted: result=%+v err=%v", result, err)
		} else if strings.Contains(err.Error(), host) {
			t.Errorf("error leaked hostname: %v", err)
		}
	}
}

func TestCheckPreservesInteriorUnicodeCombiningMarks(t *testing.T) {
	// Interior marks are not rejected by this check; they are part of many
	// valid internationalized names. A canceled context avoids network I/O.
	host := "na\u0301me.example"
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	result, err := Check(ctx, host, 443, time.Second)
	if err != nil || result.Host != host {
		t.Fatalf("interior mark rejected: result=%+v err=%v", result, err)
	}
}
