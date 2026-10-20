package doctor

import (
	"reflect"
	"testing"
)

func TestNamesFromEnvSupportsBOMAndShellExportWhitespace(t *testing.T) {
	cases := []struct {
		name string
		data string
		want []string
	}{
		{"utf8 bom", "\ufeffAPI_TOKEN=secret\nAPP_PORT=8080\n", []string{"API_TOKEN", "APP_PORT"}},
		{"bom before export", "\ufeffexport API_TOKEN=secret\n", []string{"API_TOKEN"}},
		{"export with tab", "export\tAPI_TOKEN=secret\n", []string{"API_TOKEN"}},
		{"export with repeated spaces", "export    API_TOKEN=secret\n", []string{"API_TOKEN"}},
		{"export followed by mixed whitespace", "export \t API_TOKEN=secret\n", []string{"API_TOKEN"}},
		{"ordinary name beginning export", "exported=1\nexport=2\n", []string{"export", "exported"}},
		{"duplicates and bad identifiers", "export\tAPI_TOKEN=1\nAPI_TOKEN=2\nexport\tBAD-NAME=3\n", []string{"API_TOKEN"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := namesFromEnv([]byte(tc.data)); !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("namesFromEnv()=%q, want %q", got, tc.want)
			}
		})
	}
}
