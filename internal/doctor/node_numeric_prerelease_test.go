package doctor

import "testing"

func TestCorepackNumericPrereleaseIdentifiers(t *testing.T) {
	tests := []struct {
		name    string
		version string
		valid   bool
	}{
		{"plain stable", "1.2.3", true},
		{"zero prerelease", "1.2.3-0", true},
		{"numeric prerelease", "1.2.3-10", true},
		{"mixed prerelease", "1.2.3-rc.0", true},
		{"alphanumeric leading zero", "1.2.3-01alpha", true},
		{"hyphenated identifier", "1.2.3-0-1", true},
		{"build zeros allowed", "1.2.3+001", true},
		{"build hash", "1.2.3-rc.2+sha512.abc=", true},
		{"numeric leading zero", "1.2.3-01", false},
		{"second numeric leading zero", "1.2.3-rc.001", false},
		{"deep numeric leading zero", "1.2.3-rc.2.03+build.4", false},
		{"all zero digits", "1.2.3-00", false},
		{"core leading zero", "01.2.3", false},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := validCorepackVersion(tc.version); got != tc.valid {
				t.Fatalf("validCorepackVersion(%q)=%v, want %v", tc.version, got, tc.valid)
			}
			manager, findings := selectNodePackageManager("pnpm@"+tc.version, "npm", nil)
			if tc.valid && (manager != "pnpm" || len(findings) != 0) {
				t.Fatalf("valid declaration rejected: manager=%q, findings=%+v", manager, findings)
			}
			if !tc.valid && (manager != "npm" || len(findings) != 1 || findings[0].Code != "package-manager-invalid") {
				t.Fatalf("invalid declaration accepted: manager=%q, findings=%+v", manager, findings)
			}
		})
	}
}
