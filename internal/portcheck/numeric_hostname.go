package portcheck

import (
	"net/netip"
	"strings"
)

// ambiguousNumericHost identifies malformed dotted decimal-looking IPs.
// Some resolvers interpret non-canonical numeric names as shortened/octal IPs;
// reject them instead of potentially dialing an unexpected address. A valid
// IPv4 address with a final DNS root dot is allowed for compatibility.
func ambiguousNumericHost(host string) bool {
	if !strings.Contains(host, ".") {
		return false
	}
	if addr, err := netip.ParseAddr(strings.TrimSuffix(host, ".")); err == nil && addr.Is4() {
		return false
	}
	for i := 0; i < len(host); i++ {
		if host[i] != '.' && (host[i] < '0' || host[i] > '9') {
			return false
		}
	}
	return true
}
