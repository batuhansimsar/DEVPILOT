package doctor

import "testing"

func TestDeclaredNodeManager(t *testing.T) {
	cases := []struct{ spec, want string }{
		{"npm@10.2.0", "npm"},
		{"pnpm@9.0.0", "pnpm"},
		{"yarn@4.2.0+sha224.foo", "yarn"},
		{"bun@1.1.0", "bun"},
		{"pnpm", ""},
		{"pnpm@", ""},
		{"yarn@4.0.0 --dangerous", ""},
		{"arbitrary-executable@1.2.3", ""},
		{"@scope/tool@1.2.3", ""},
	}
	for _, tc := range cases {
		t.Run(tc.spec, func(t *testing.T) {
			if got := declaredNodeManager(tc.spec); got != tc.want {
				t.Fatalf("declaredNodeManager(%q)=%q, want %q", tc.spec, got, tc.want)
			}
		})
	}
}
