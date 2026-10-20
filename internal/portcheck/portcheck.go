// Package portcheck provides a bounded TCP connectivity probe. It does not
// execute subprocesses, inspect credentials, or send application data.
package portcheck

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/netip"
	"strconv"
	"syscall"
	"strings"
	"time"
	"unicode"
)

// Result describes a single TCP dial attempt. A failed connection is a
// reachable=false result, not a configuration error.
type Result struct {
	Host      string  `json:"host"`
	Port      int     `json:"port"`
	Reachable bool    `json:"reachable"`
	LatencyMS float64 `json:"latency_ms"`
	Error     string  `json:"error,omitempty"`
}

// safeDialError reports actionable failure classes without forwarding potentially
// sensitive hostnames, IP addresses, or operating-system diagnostics. Dial
// errors can include untrusted resolver responses and the full remote address.
func safeDialError(err error) string {
	if errors.Is(err, context.Canceled) {
		return "connection canceled"
	}
	if errors.Is(err, context.DeadlineExceeded) {
		return "connection timed out"
	}
	var networkError net.Error
	if errors.As(err, &networkError) && networkError.Timeout() {
		return "connection timed out"
	}
	if errors.Is(err, syscall.ECONNREFUSED) {
		return "connection refused"
	}
	if errors.Is(err, syscall.ECONNRESET) {
		return "connection reset"
	}
	if errors.Is(err, syscall.ECONNABORTED) {
		return "connection aborted"
	}
	if errors.Is(err, syscall.EADDRNOTAVAIL) {
		return "local address unavailable"
	}
	if errors.Is(err, syscall.ENETUNREACH) {
		return "network unreachable"
	}
	if errors.Is(err, syscall.EHOSTUNREACH) {
		return "host unreachable"
	}
	var dnsError *net.DNSError
	if errors.As(err, &dnsError) {
		if dnsError.IsNotFound {
			return "DNS name not found"
		}
		return "DNS resolution failed"
	}
	return "TCP connection failed"
}

// Check attempts one TCP connection to the explicitly supplied host and port.
// The timeout applies to DNS resolution and dialing via the context.
// LatencyMS measures the dial attempt, including DNS resolution when needed.
func Check(ctx context.Context, host string, port int, timeout time.Duration) (Result, error) {
	if ctx == nil {
		return Result{}, fmt.Errorf("context must not be nil")
	}
	if host == "" || host != strings.TrimSpace(host) || strings.IndexFunc(host, func(r rune) bool {
		return unicode.IsControl(r) || unicode.Is(unicode.Cf, r)
	}) >= 0 {
		return Result{}, fmt.Errorf("host must be a nonempty hostname or IP address without surrounding whitespace, control, or formatting characters")
	}
	// A bracketed IPv6 literal is common when copied from a URL. DialContext
	// needs the address without brackets because JoinHostPort adds them.
	// Reject malformed or non-IPv6 bracketed values as configuration errors.
	dialHost := host
	if strings.ContainsAny(host, "[]") {
		if len(host) < 3 || host[0] != '[' || host[len(host)-1] != ']' {
			return Result{}, fmt.Errorf("host has malformed IPv6 brackets")
		}
		dialHost = host[1 : len(host)-1]
		ip, err := netip.ParseAddr(dialHost)
		if err != nil || !ip.Is6() {
			return Result{}, fmt.Errorf("bracketed host must be a valid IPv6 address")
		}
	}
	if strings.IndexFunc(host, unicode.IsSpace) >= 0 || strings.ContainsAny(host, "/\\@?#") {
		return Result{}, fmt.Errorf("host must not contain whitespace or URL delimiters")
	}
	// Colons in a host are valid only for IPv6 literals, never for a
	// second port embedded in the host argument.
	if strings.Contains(dialHost, ":") {
		if ip, err := netip.ParseAddr(dialHost); err != nil || !ip.Is6() {
			return Result{}, fmt.Errorf("host contains an invalid IPv6 address or embedded port")
		}
	}
	if port < 1 || port > 65535 {
		return Result{}, fmt.Errorf("port must be between 1 and 65535")
	}
	if timeout < 100*time.Millisecond || timeout > 30*time.Second {
		return Result{}, fmt.Errorf("timeout must be between 100ms and 30s")
	}
	result := Result{Host: host, Port: port}
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	started := time.Now()
	conn, err := (&net.Dialer{}).DialContext(ctx, "tcp", net.JoinHostPort(dialHost, strconv.Itoa(port)))
	result.LatencyMS = float64(time.Since(started)) / float64(time.Millisecond)
	if err != nil {
		result.Error = safeDialError(err)
		return result, nil
	}
	_ = conn.Close()
	result.Reachable = true
	return result, nil
}
