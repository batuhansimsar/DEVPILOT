package portcheck

import (
	"net/netip"
	"strings"
	"unicode"
)

// ambiguousNumericHost identifies non-canonical numeric IPv4 spellings.
// System resolvers may treat decimal integers, octal numbers, hexadecimal
// numbers, and abbreviated dotted forms as IP addresses (e.g. 2130706433,
// 017700000001, or 0x7f000001 all resolve to 127.0.0.1 on some systems).
// Reject such aliases rather than dialing a different endpoint than the user
// expects. Canonical IPv4 addresses and their trailing-root-dot forms remain
// valid; ordinary DNS names with non-numeric labels are unaffected.
func ambiguousNumericHost(host string) bool {
	withoutRootDot := strings.TrimSuffix(host, ".")
	if addr, err := netip.ParseAddr(withoutRootDot); err == nil && addr.Is4() {
		return false
	}
	if withoutRootDot == "" {
		return false
	}
	for _, label := range strings.Split(withoutRootDot, ".") {
		if !numericIPv4Component(label) {
			return false
		}
	}
	return true
}

// numericIPv4Component recognizes numeric-only hostname labels, including
// legacy ASCII inet_aton forms and Unicode decimal digits. Some DNS libraries
// normalize Unicode digits; reject numeric-looking aliases before resolution.
func numericIPv4Component(label string) bool {
	if label == "" {
		return false
	}
	if len(label) > 2 && label[0] == '0' && (label[1] == 'x' || label[1] == 'X') {
		for i := 2; i < len(label); i++ {
			c := label[i]
			if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')) {
				return false
			}
		}
		return true
	}
	for _, r := range label {
		if !unicode.IsDigit(r) {
			return false
		}
	}
	return true
}
