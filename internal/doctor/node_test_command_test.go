package doctor

import (
	"reflect"
	"testing"
)

func TestNodeTestArgs(t *testing.T) {
	for _, tc := range []struct {
		executable string
		want       []string
	}{
		{"npm", []string{"test"}},
		{"pnpm", []string{"test"}},
		{"yarn", []string{"test"}},
		{"bun", []string{"run", "test"}},
	} {
		t.Run(tc.executable, func(t *testing.T) {
			if got := nodeTestArgs(tc.executable); !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("nodeTestArgs(%q) = %v, want %v", tc.executable, got, tc.want)
			}
		})
	}
}
