package doctor

import (
	"strings"
	"testing"
)

func TestDeclaredNodeManager(t *testing.T) {
	cases := []struct{ spec, want string }{
		{"npm@10.2.0", "npm"},
		{"pnpm@9.0.0", "pnpm"},
		{"yarn@4.2.0+sha224.foo", "yarn"},
		{"bun@1.1.0", "bun"},
		{"yarn@4.0.0-rc.1+build.3", "yarn"},
		{"pnpm", ""},
		{"pnpm@", ""},
		{"yarn@4.0.0 --dangerous", ""},
		{"arbitrary-executable@1.2.3", ""},
		{"@scope/tool@1.2.3", ""},
		{"pnpm@latest", ""},
		{"pnpm@^9.0.0", ""},
		{"pnpm@9.0", ""},
		{"pnpm@9.0.0@other", ""},
		{"pnpm@9.0.0\u202e", ""},
		{"pnpm@" + strings.Repeat("1", 129), ""},
	}
	for _, tc := range cases {
		t.Run(tc.spec, func(t *testing.T) {
			if got := declaredNodeManager(tc.spec); got != tc.want {
				t.Fatalf("declaredNodeManager(%q)=%q, want %q", tc.spec, got, tc.want)
			}
		})
	}
}
