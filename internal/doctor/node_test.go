package doctor

import "testing"

func TestSelectNodePackageManager(t *testing.T) {
	tests := []struct {
		name, declaration, fallback, expected, warning string
		locks                                          []string
	}{
		{name: "no declaration", fallback: "pnpm", expected: "pnpm"},
		{name: "declared without lockfile", declaration: "yarn@4.0.0", fallback: "npm", expected: "yarn"},
		{name: "integrity hash", declaration: "pnpm@9.1.0+sha512.abc", fallback: "npm", expected: "pnpm"},
		{name: "prerelease and build", declaration: "yarn@4.0.0-rc.1+build.3", fallback: "npm", expected: "yarn"},
		{name: "matching lockfile", declaration: "bun@1.2.0", fallback: "bun", locks: []string{"bun.lock"}, expected: "bun"},
		{name: "mismatched lockfile", declaration: "yarn@4.0.0", fallback: "pnpm", locks: []string{"pnpm-lock.yaml"}, expected: "yarn", warning: "package-manager-lock-mismatch"},
		{name: "multiple stale lockfiles", declaration: "npm@10.0.0", fallback: "pnpm", locks: []string{"pnpm-lock.yaml", "yarn.lock", "package-lock.json"}, expected: "npm", warning: "package-manager-lock-mismatch"},
		{name: "unknown executable", declaration: "curl@1.0.0", fallback: "npm", expected: "npm", warning: "package-manager-invalid"},
		{name: "missing version", declaration: "pnpm", fallback: "npm", expected: "npm", warning: "package-manager-invalid"},
		{name: "blank version", declaration: "npm@", fallback: "npm", expected: "npm", warning: "package-manager-invalid"},
		{name: "spaces", declaration: "npm@1 2", fallback: "npm", expected: "npm", warning: "package-manager-invalid"},
		{name: "incomplete semver", declaration: "npm@10.0", fallback: "pnpm", expected: "pnpm", warning: "package-manager-invalid"},
		{name: "dist tag", declaration: "npm@latest", fallback: "pnpm", expected: "pnpm", warning: "package-manager-invalid"},
		{name: "range", declaration: "pnpm@^9.0.0", fallback: "npm", expected: "npm", warning: "package-manager-invalid"},
		{name: "embedded separator", declaration: "npm@1.2.3@other", fallback: "npm", expected: "npm", warning: "package-manager-invalid"},
		{name: "leading zero", declaration: "npm@01.2.3", fallback: "npm", expected: "npm", warning: "package-manager-invalid"},
		{name: "unsafe suffix", declaration: "npm@1.2.3;echo", fallback: "npm", expected: "npm", warning: "package-manager-invalid"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			name, findings := selectNodePackageManager(tc.declaration, tc.fallback, tc.locks)
			if name != tc.expected {
				t.Fatalf("got %q, want %q", name, tc.expected)
			}
			if tc.warning == "" && len(findings) != 0 {
				t.Fatalf("unexpected warnings: %+v", findings)
			}
			if tc.warning != "" && (len(findings) != 1 || findings[0].Code != tc.warning) {
				t.Fatalf("warnings: %+v, want %s", findings, tc.warning)
			}
		})
	}
}
