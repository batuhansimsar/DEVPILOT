// devpilot-web is a local-only browser view of devpilot doctor reports.
package main

import (
	"context"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"time"

	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
	"github.com/batuhansimsar/DEVPILOT/internal/reportui"
)

func run(args []string) error {
	flags := flag.NewFlagSet("devpilot-web", flag.ContinueOnError)
	dir := flags.String("path", ".", "project directory")
	bind := flags.String("listen", "127.0.0.1:3847", "loopback listening address")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return fmt.Errorf("unexpected positional arguments: %v", flags.Args())
	}
	host, _, err := net.SplitHostPort(*bind)
	if err != nil {
		return fmt.Errorf("invalid listen address: %w", err)
	}
	ip := net.ParseIP(host)
	if host != "localhost" && (ip == nil || !ip.IsLoopback()) {
		return fmt.Errorf("refusing non-loopback listener: %q", *bind)
	}
	if _, err := doctor.Inspect(*dir); err != nil {
		return fmt.Errorf("cannot inspect project: %w", err)
	}
	srv := &http.Server{Addr: *bind, Handler: reportui.Handler(*dir, func(p string) (any, error) { return doctor.Inspect(p) }), ReadHeaderTimeout: 5 * time.Second}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	go func() {
		<-ctx.Done()
		closeCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(closeCtx)
	}()
	fmt.Printf("DevPilot dashboard: http://%s\n", *bind)
	err = srv.ListenAndServe()
	if err == http.ErrServerClosed {
		return nil
	}
	return err
}
func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, "devpilot-web:", err)
		os.Exit(1)
	}
}
