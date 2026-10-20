// Package dashboard presents a read-only view of the existing doctor report.
// The scanner is injected so HTTP request handling never executes project code.
package dashboard

import (
	"encoding/json"
	"html/template"
	"net"
	"net/http"
	"strings"
)

// Handler serves the report on / and /api/report. The caller must bind to
// 127.0.0.1; Handler additionally rejects non-local Host headers to reduce
// exposure to DNS rebinding. The source must return a struct compatible with
// doctor.Report (Path, Languages, Frameworks, PackageManager, Tests, Findings).
func Handler(source func() (any, error)) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		respond(w, r, source, false)
	})
	mux.HandleFunc("/api/report", func(w http.ResponseWriter, r *http.Request) {
		respond(w, r, source, true)
	})
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		host := r.Host
		if parsed, _, err := net.SplitHostPort(host); err == nil {
			host = parsed
		}
		if host != "127.0.0.1" && host != "localhost" && host != "::1" && host != "[::1]" {
			http.Error(w, "invalid Host", http.StatusForbidden)
			return
		}
		mux.ServeHTTP(w, r)
	})
}

func respond(w http.ResponseWriter, r *http.Request, source func() (any, error), asJSON bool) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		w.Header().Set("Allow", "GET, HEAD")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	report, err := source()
	if err != nil {
		http.Error(w, "Unable to inspect the selected workspace", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("X-Frame-Options", "DENY")
	w.Header().Set("Referrer-Policy", "no-referrer")
	w.Header().Set("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
	if asJSON {
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		if err := json.NewEncoder(w).Encode(report); err != nil {
			return
		}
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := page.Execute(w, report); err != nil {
		return
	}
}

var page = template.Must(template.New("dashboard").Funcs(template.FuncMap{
	"join":      func(v []string) string { return strings.Join(v, ", ") },
	"spacejoin": func(v []string) string { return strings.Join(v, " ") },
}).Parse("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n<title>DevPilot — Local dashboard</title>\n<style>\n:root{color-scheme:dark light;font:16px/1.6 system-ui,-apple-system,sans-serif;background:#0d1525;color:#edf2fa}\n*{box-sizing:border-box}body{margin:0}header{background:#15253b;border-bottom:1px solid #394864;padding:18px max(20px,calc((100vw - 1050px)/2));font-size:22px;font-weight:800;letter-spacing:-.04em}header em{font-style:normal;color:#79d6ff}\nmain{max-width:1050px;margin:auto;padding:34px 20px 60px}h1{font-size:clamp(26px,4vw,38px);margin:0}h2{font-size:20px;margin:38px 0 10px}.dim{color:#b6c3d5}.meta{display:flex;flex-wrap:wrap;gap:12px;margin:25px 0}.tile{background:#17243a;border:1px solid #384b65;border-radius:14px;flex:1;min-width:180px;padding:18px}.tile strong{display:block;font-size:21px;overflow-wrap:anywhere;margin-top:4px}.panel{background:#17243a;border:1px solid #384b65;border-radius:12px;padding:18px;margin:12px 0;border-left:4px solid #6dbbe6}\n.panel.warning{border-left-color:#f9cd78}.panel.info{border-left-color:#87c1f2}.panel.pass{border-left-color:#78d4b6}.panel.error{border-left-color:#ff8585}\nsummary{cursor:pointer;font-weight:700}.level{font-size:11px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#aad7f2}p{margin:8px 0}code{background:#253854;padding:3px 6px;border-radius:5px;overflow-wrap:anywhere}a{color:#80d7ff}a:focus-visible,summary:focus-visible{outline:3px solid #86e1ff;outline-offset:3px}.top{display:flex;flex-wrap:wrap;gap:15px;align-items:center;justify-content:space-between}\n@media(prefers-color-scheme:light){:root{background:#f4f7fa;color:#1b2a42}header{background:#e8f2fc;border-color:#becbda}.dim{color:#556981}.tile,.panel{background:#fff;border-color:#d1dbe6}.level{color:#366184}code{background:#e8eff8}}\n</style></head><body><header>Dev<em>Pilot</em> <small class=\"dim\">/ developer diagnostics</small></header>\n<main><div class=\"top\"><div><h1>Project overview</h1><p class=\"dim\">Local and read-only · No AI or repository scripts executed</p></div><a href=\"/\">Refresh diagnostics ↻</a></div>\n<p><small>Workspace: <code>{{.Path}}</code></small></p>\n<div class=\"meta\"><div class=\"tile\"><small class=\"dim\">Languages</small><strong>{{if .Languages}}{{join .Languages}}{{else}}Not detected{{end}}</strong></div><div class=\"tile\"><small class=\"dim\">Frameworks</small><strong>{{if .Frameworks}}{{join .Frameworks}}{{else}}Not detected{{end}}</strong></div><div class=\"tile\"><small class=\"dim\">Package manager</small><strong>{{if .PackageManager}}{{.PackageManager}}{{else}}Not detected{{end}}</strong></div><div class=\"tile\"><small class=\"dim\">Findings</small><strong>{{len .Findings}}</strong></div></div>\n<h2>Diagnostics</h2>{{if .Findings}}{{range .Findings}}<section class=\"panel {{.Level}}\"><span class=\"level\">{{.Level}} · {{.Code}}</span><details open><summary>{{.Message}}</summary>{{if .Remedy}}<p class=\"dim\"><b>Next step:</b> {{.Remedy}}</p>{{end}}</details></section>{{end}}{{else}}<p>No findings in the supported inspection scope.</p>{{end}}\n<h2>Test discovery</h2>{{if .Tests}}<div class=\"panel\"><code>{{.Tests.Executable}} {{spacejoin .Tests.Arguments}}</code><p class=\"dim\">Test scripts are never run by this dashboard. Use <code>devpilot test --trust</code> only for repositories you trust.</p></div>{{else}}<p class=\"dim\">No test command discovered.</p>{{end}}\n<p><a href=\"/api/report\">View JSON report</a></p></main></body></html>"))
