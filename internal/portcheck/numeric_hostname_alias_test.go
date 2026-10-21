package portcheck

import "testing"

func TestAmbiguousNumericHostRejectsLegacyIPv4Aliases(t *testing.T) {
	for _, host := range []string{
		"2130706433",       // one-component decimal
		"017700000001",     // one-component octal
		"0x7f000001",       // one-component hexadecimal
		"0X7F000001",       // uppercase hexadecimal
		"127.1",            // short dotted decimal
		"127.000.000.001",  // octal-looking dotted decimal
		"127.0x0.0.1",      // mixed hexadecimal and decimal
		"0x7f.0.0x0.0x1",  // all-hex dotted notation
		"999.999.999.999", // invalid dotted numeric address
	} {
		t.Run(host, func(t *testing.T) {
			if !ambiguousNumericHost(host) {
				t.Fatalf("numeric IPv4 alias %q was accepted", host)
			}
		})
	}
}

func TestAmbiguousNumericHostPreservesCanonicalIPv4AndDNS(t *testing.T) {
	for _, host := range []string{
		"127.0.0.1", "127.0.0.1.", "192.168.1.20",
		"example.org", "api.123", "bücher.example", "0x7f000001.example",
		"a123", "", "127.0.0.1..", // Other validation rejects malformed syntax.
	} {
		t.Run(host, func(t *testing.T) {
			if ambiguousNumericHost(host) {
				t.Fatalf("canonical IPv4 or DNS host %q was rejected", host)
			}
		})
	}
}
