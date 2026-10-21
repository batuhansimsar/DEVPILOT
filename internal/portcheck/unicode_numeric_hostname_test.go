package portcheck

import "testing"

// DNS libraries can map non-ASCII decimal digits before name resolution.
// These numeric-looking hostnames must not bypass the legacy IPv4 alias guard.
func TestRejectsUnicodeNumericIPv4Aliases(t *testing.T) {
	for _, host := range []string{
		"１２７.０.０.１", // fullwidth digits
		"١٢٧.٠.٠.١", // Arabic-Indic digits
		"１２７.0.0.1", // mixed Unicode and ASCII digits
		"１２７",       // all-numeric single-label address
	} {
		t.Run(host, func(t *testing.T) {
			if !ambiguousNumericHost(host) {
				t.Errorf("numeric-looking hostname bypassed alias validation: %q", host)
			}
		})
	}
}

func TestUnicodeDigitsInsideDNSNameRemainValid(t *testing.T) {
	for _, host := range []string{"api.１２３", "١٢٧.example", "bücher.１２３"} {
		t.Run(host, func(t *testing.T) {
			if ambiguousNumericHost(host) {
				t.Errorf("regular DNS hostname rejected: %q", host)
			}
		})
	}
}
