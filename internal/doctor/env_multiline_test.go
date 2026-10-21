package doctor

import (
	"reflect"
	"strings"
	"testing"
)

func TestEnvQuotedMultilineDoesNotForgeKeys(t *testing.T) {
	cases := []struct {
		name, source string
		want         []string
	}{
		{"double-quoted", "BANNER=\"first line\nFAKE=not-a-key\nlast line\"\nREAL=present\n", []string{"BANNER", "REAL"}},
		{"single-quoted", "export MESSAGE='header\rPHANTOM=hidden\rfooter'\rTRUE=1", []string{"MESSAGE", "TRUE"}},
		{"escaped quote", "FIRST=\"line \\\" still quoted\nFORGED=no\nclose\"\nSECOND=yes", []string{"FIRST", "SECOND"}},
		{"escaped next line quote", "FIRST=\"line ending slash\\\n\"not closed yet\nFORGED=no\nend\"\nSECOND=yes", []string{"FIRST", "SECOND"}},
		{"unterminated", "BANNER=\"never closed\nPHANTOM=not-a-key", []string{"BANNER"}},
		{"closed single-line", "ONE=\"done\"\nTWO=yes", []string{"ONE", "TWO"}},
		{"CRLF", "BANNER=\"begin\r\nFALSE=no\r\nend\"\r\nREAL=yes", []string{"BANNER", "REAL"}},
		{"unicode separators", "TEXT=first\u2028FAKE=no\n\u2028OTHER=no\nREAL=yes", []string{"REAL", "TEXT"}},
		{"bom and export", "\ufeffexport API_KEY = redacted\n\t OTHER = x", []string{"API_KEY", "OTHER"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := namesFromEnv([]byte(tc.source))
			if !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("namesFromEnv() = %q, want %q", got, tc.want)
			}
		})
	}
}

// An apparent KEY=value inside a local .env's quoted multiline value must
// not be allowed to satisfy a required declaration in .env.example.
func TestInspectEnvMultilineCannotMaskMissingKey(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, ".env.example", "REQUIRED=sample\nBANNER=sample\n")
	write(t, dir, ".env", "BANNER=\"hello\nREQUIRED=forged\nworld\"\n")
	report, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	for _, f := range report.Findings {
		if f.Code == "env-local-missing-keys" {
			if !strings.Contains(f.Message, "REQUIRED") || strings.Contains(f.Message, "forged") {
				t.Fatalf("unexpected missing-keys finding: %q", f.Message)
			}
			return
		}
	}
	t.Fatal("expected missing REQUIRED warning for multiline value")
}
