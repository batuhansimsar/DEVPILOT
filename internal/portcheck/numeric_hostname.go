package portcheck

import (
	"net/netip"
	"strings"
)

// ambiguousNumericHost identifies non-canonical IPv4-like names that a system
// resolver could reinterpret as shorthand, octal, hexadecimal, or integer IPs.
// Canonical IPv4 and its optional terminal DNS root dot remain supported.
func ambiguousNumericHost(host string) bool {
	if addr, err := netip.ParseAddr(strings.TrimSuffix(host, ".")); err == nil && addr.Is4() {
		return false
	}
	// Legacy IPv4 parsers accept one to four components, with each component
	// expressed in decimal, octal, or hexadecimal. Reject all-numeric forms
	// before DNS resolution, including those with empty dotted components.
	for _, label := range strings.Split(strings.TrimSuffix(host, "."), ".") {
		if label == "" {
			continue
		}
		base := 10
		if strings.HasPrefix(label, "0x") || strings.HasPrefix(label, "0X") {
			base = 16
			label = label[2:]
			if label == "" {
				return false
			}
		}
		for i := 0; i < len(label); i++ {
			ch := label[i]
			if ch >= '0' && ch <= '9' {
				continue
			}
			if base == 16 && ((ch >= 'a' && ch <= 'f') || (ch >= 'A' && ch <= 'F')) {
				continue
			}
			return false
		}
	}
	return true
}
