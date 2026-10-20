// Package portcheck provides a bounded TCP connectivity probe. It does not
// execute subprocesses, inspect credentials, or send application data.
package portcheck

import (
	"context"
	"fmt"
	"net"
	"strconv"
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

// Check attempts one TCP connection to the explicitly supplied host and port.
// The timeout applies to DNS resolution and dialing via the context.
// LatencyMS measures the dial attempt, including DNS resolution when needed.
func Check(ctx context.Context, host string, port int, timeout time.Duration) (Result, error) {
	if host == "" || host != strings.TrimSpace(host) || strings.IndexFunc(host, unicode.IsControl) >= 0 {
		return Result{}, fmt.Errorf("host must be a nonempty hostname or IP address without surrounding whitespace or control characters")
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
	conn, err := (&net.Dialer{}).DialContext(ctx, "tcp", net.JoinHostPort(host, strconv.Itoa(port)))
	result.LatencyMS = float64(time.Since(started)) / float64(time.Millisecond)
	if err != nil {
		result.Error = err.Error()
		return result, nil
	}
	_ = conn.Close()
	result.Reachable = true
	return result, nil
}
