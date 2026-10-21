package portcheck

import "testing"

// Legacy IPv4 address forms can resolve to a different endpoint than a reader
// expects. Reject the entire numeric syntax class before DNS or TCP dialing.
func TestRejectsLegacyIPv4Aliases(t *testing.T) {
	for _, host := range []string{
		"2130706433",      // single-number IPv4
		"017700000001",    // octal IPv4
		"0x7f000001",      // hexadecimal IPv4
		"0X7F000001",      // uppercase hexadecimal marker
		"0x7f.1",          // shortened hexadecimal dotted address
		"127.0x0.0.1",     // mixed decimal/hexadecimal
		"0x7f.0.0.01",     // mixed hex/octal
		"0x7f000001.",     // root-qualified hexadecimal alias
		"127.1",           // shortened decimal form
		"127.000.000.001", // octal-looking dotted decimal
		"1.2.3.4.5",       // more than four components
	} {
		t.Run(host, func(t *testing.T) {
			if !ambiguousNumericHost(host) {
				t.Errorf("accepted ambiguous IPv4 address: %q", host)
			}
		})
	}
}

func TestNumericHostnameDetectionAllowsCanonicalIPAndDNS(t *testing.T) {
	for _, host := range []string{
		"127.0.0.1", "127.0.0.1.", "1.2.3.4", "::1", "[::1]",
		"example.org", "api.123", "123.example", "api.0x12", "bücher.example",
	} {
		t.Run(host, func(t *testing.T) {
			if ambiguousNumericHost(host) {
				t.Errorf("rejected canonical address or DNS hostname: %q", host)
			}
		})
	}
}
