package doctor

import (
	"encoding/json"
	"testing"
)

func TestDoctorIgnoresNonRunnableNodeTestScripts(t *testing.T) {
	cases := []struct {
		name, script string
		runnable     bool
	}{
		{"empty", "", false},
		{"whitespace", "  ", false},
		{"npm-init-placeholder", `echo "Error: no test specified" && exit 1`, false},
		{"real-test", "node --test", true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			pkg, err := json.Marshal(map[string]any{
				"scripts": map[string]string{"test": tc.script},
			})
			if err != nil {
				t.Fatal(err)
			}
			write(t, root, "package.json", string(pkg))
			report, err := Inspect(root)
			if err != nil {
				t.Fatal(err)
			}
			if got := report.Tests != nil; got != tc.runnable {
				t.Fatalf("test discovery = %v, want %v: %+v", got, tc.runnable, report)
			}
			if got := finding(report, "js-test-script-placeholder"); got == tc.runnable {
				t.Fatalf("placeholder finding = %v, runnable = %v", got, tc.runnable)
			}
			if tc.runnable && (report.Tests.Executable != "npm" || len(report.Tests.Arguments) != 1 || report.Tests.Arguments[0] != "test") {
				t.Fatalf("unexpected test command: %+v", report.Tests)
			}
		})
	}
}
