package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
)

func main() { os.Exit(run(os.Args[1:],os.Stdout,os.Stderr)) }

func run(args []string, out, errs io.Writer) int {
	if len(args)==0 {usage(out);return 0}
	switch args[0] {
	case "help","-h","--help": usage(out);return 0
	case "version","--version":fmt.Fprintln(out,"DevPilot v0.1.0-dev");return 0
	case "doctor","inspect":return runDoctor(args[1:],out,errs)
	case "test":return runTest(args[1:],out,errs)
	default:fmt.Fprintf(errs,"Unknown command %q. Run devpilot help.\n",args[0]);return 2
	}
}

func usage(out io.Writer) {
	fmt.Fprint(out,DevPilot — developer project diagnostics (no AI account required)

Usage:
  devpilot doctor [--json] [--strict] [path]
  devpilot inspect [--json] [path]
  devpilot test [--list] [path]
  devpilot test --run --trust-workspace [--only ID] [--timeout 120s] [path]

Inspection is read-only. Test execution is opt-in and may run arbitrary
project code; only grant --trust-workspace for repositories you trust.
`)
}

func parsePath(pos []string) (string,error) {
	if len(pos)>1 {return "",errors.New("expected at most one workspace path")}
	if len(pos)==1 {return pos[0],nil}
	return ".",nil
}

func runDoctor(args []string, out, errs io.Writer) int {
	fs:=flag.NewFlagSet("doctor",flag.ContinueOnError)
	fs.SetOutput(errs)
	jsonOutput:=fs.Bool("json",false,"write machine-readable JSON")
	strict:=fs.Bool("strict",false,"fail if errors are found")
	if err:=fs.Parse(args);err!=nil{return 2}
	path,err:=parsePath(fs.Args());if err!=nil {fmt.Fprintln(errs,err);return 2}
	r,err:=doctor.Analyze(context.Background(),path)
	if err!=nil {fmt.Fprintln(errs,"Analysis failed:",err);return 1}
	if *jsonOutput {
		enc:=json.NewEncoder(out);enc.SetIndent("","  ")
		if err:=enc.Encode(r);err!=nil {fmt.Fprintln(errs,err);return 1}
	} else {printReport(out,r)}
	if *strict {for _, f:=range r.Findings {if f.Severity=="error" {return 1}}}
	return 0
}

func printReport(out io.Writer,r doctor.Report) {
	fmt.Fprintf(out,"DevPilot doctor — %s\nScanned %d files (bounded, no workspace commands executed).\n",r.Workspace,r.FilesScanned)
	if len(r.Technologies)>0 {
		fmt.Fprintln(out,"\nTechnologies:")
		for _,t:=range r.Technologies {fmt.Fprintf(out,"  - %s [%s]\n",t.Name,t.Evidence)}
	}
	fmt.Fprintf(out,"\nGit: %s\n",r.Git.Status)
	if len(r.TestPlans)>0 {
		fmt.Fprintln(out,"\nDiscovered test commands (not executed):")
		for _,p:=range r.TestPlans {fmt.Fprintf(out,"  - %s: %s %s [%s]\n",p.ID,p.Command,strings.Join(p.Args," "),p.Evidence)}
	}
	if len(r.Findings)>0 {
		fmt.Fprintln(out,"\nFindings:")
		for _,f:=range r.Findings {
			fmt.Fprintf(out,"  [%s] %s: %s",strings.ToUpper(f.Severity),f.Code,f.Message)
			if f.Evidence!=""{fmt.Fprintf(out," (%s)",f.Evidence)}
			fmt.Fprintln(out)
			if f.Remedy!="" {fmt.Fprintf(out,"    Next: %s\n",f.Remedy)}
		}
	}
}

func runTest(args []string,out,errs io.Writer) int {
	fs:=flag.NewFlagSet("test",flag.ContinueOnError);fs.SetOutput(errs)
	list:=fs.Bool("list",false,"list discovered tests (default)")
	execute:=fs.Bool("run",false,"execute discovered test commands")
	trusted:=fs.Bool("trust-workspace",false,"acknowledge workspace commands may execute arbitrary code")
	only:=fs.String("only","","run one discovered test plan ID")
	timeout:=fs.Duration("timeout",120*time.Second,"per-command timeout")
	if err:=fs.Parse(args);err!=nil{return 2}
	if *execute && !*trusted {fmt.Fprintln(errs,"Refusing to execute untrusted workspace commands. Add --trust-workspace only after reviewing this repository.");return 2}
	if *timeout<=0 || *timeout>30*time.Minute {fmt.Fprintln(errs,"--timeout must be between 1ns and 30m");return 2}
	path,err:=parsePath(fs.Args());if err!=nil {fmt.Fprintln(errs,err);return 2}
	r,err:=doctor.Analyze(context.Background(),path)
	if err!=nil {fmt.Fprintln(errs,"Analysis failed:",err);return 1}
	if len(r.TestPlans)==0 {fmt.Fprintln(out,"No test commands discovered.");return 0}
	if !*execute || *list && !*execute {
		for _,p:=range r.TestPlans {fmt.Fprintf(out,"%s: %s %s (in %s)\n",p.ID,p.Command,strings.Join(p.Args," "),p.Directory)}
		return 0
	}
	selected:=0
	failed:=false
	for _,p:=range r.TestPlans {
		if *only!="" && *only!=p.ID {continue}
		selected++
		fmt.Fprintf(out,"\nRunning %s: %s %s\n",p.ID,p.Command,strings.Join(p.Args," "))
		ctx,cancel:=context.WithTimeout(context.Background(),*timeout)
		cmd:=exec.CommandContext(ctx,p.Command,p.Args...) // never pass through a shell
		cmd.Dir=p.Directory
		cmd.Stdout=out;cmd.Stderr=errs
		err:=cmd.Run()
		if err!=nil {failed=true;fmt.Fprintf(errs,"Test plan %s failed: %v\n",p.ID,err)}
		cancel()
	}
	if selected==0 {fmt.Fprintln(errs,"No matching test plan ID.");return 2}
	if failed {return 1}
	return 0
}
