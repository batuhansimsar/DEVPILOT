package main

import (
    "encoding/json"
    "errors"
    "flag"
    "fmt"
    "io"
    "os"
    "path/filepath"
    "regexp"
    "sort"
    "strings"
)

// Candidate is a command suggestion, never an executed or verified command.
type Candidate struct {
    Command string `json:"command"`
    Purpose string `json:"purpose"`
    Evidence string `json:"evidence"`
    Verified bool `json:"verified"`
}

type Report struct {
    Status string `json:"status"`
    Candidates []Candidate `json:"candidates"`
    Warnings []string `json:"warnings,omitempty"`
}

const maxFileSize = 1024 * 1024

// readFile rejects symlink and special-file inputs, and does not follow paths
// referenced by project configuration.
func readFile(root, filename string) ([]byte, bool, error) {
    path := filepath.Join(root, filename)
    info, err := os.Lstat(path)
    if errors.Is(err, os.ErrNotExist) { return nil, false, nil }
    if err != nil { return nil, false, err }
    if !info.Mode().IsRegular() { return nil, false, fmt.Errorf("%s is not a regular file", filename) }
    if info.Size() > maxFileSize { return nil, false, fmt.Errorf("%s exceeds the 1 MiB limit", filename) }
    data, err := os.ReadFile(path)
    return data, true, err
}

var safeName = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9:_-]*$`)
var targetPattern = regexp.MustCompile(`(?m)^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]|$)`)

func purpose(name string) string {
    switch {
    case name=="dev" || name=="start" || name=="run": return "run"
    case name=="test" || strings.HasPrefix(name,"test:"): return "test"
    case name=="build" || strings.HasPrefix(name,"build:"): return "build"
    case name=="lint" || strings.HasPrefix(name,"lint:"): return "lint"
    case name=="check" || strings.HasPrefix(name,"check:"): return "check"
    }
    return ""
}

func manager(root, declared string) (string, []string, error) {
    locks:=map[string]string{
        "package-lock.json":"npm", "pnpm-lock.yaml":"pnpm",
        "yarn.lock":"yarn", "bun.lock":"bun", "bun.lockb":"bun",
    }
    found:=map[string]bool{}
    for name,tool:=range locks {
        _,ok,err:=readFile(root,name)
        if err!=nil {return "",nil,err}
        if ok {found[tool]=true}
    }
    warnings:=[]string{}
    if len(found)>1 {warnings=append(warnings,"Conflicting JavaScript lockfiles; review package manager before running scripts.")}
    named:=strings.SplitN(declared,"@",2)[0]
    switch named {
    case "npm","pnpm","yarn","bun":
        if len(found)>0 && !found[named] {warnings=append(warnings,"packageManager disagrees with detected lockfile(s).")}
        return named,warnings,nil
    case "":
    default:
        warnings=append(warnings,"Unsupported packageManager declaration.")
    }
    if len(found)==1 {for tool:=range found {return tool,warnings,nil}}
    if len(found)>1 {return "",warnings,nil}
    warnings=append(warnings,"No recognized lockfile; npm is an unverified fallback.")
    return "npm",warnings,nil
}

func discover(root string) (Report,error) {
    report:=Report{Status:"no-manifest", Candidates:[]Candidate{}}
    info,err:=os.Stat(root)
    if err!=nil {return report,fmt.Errorf("workspace: %w",err)}
    if !info.IsDir() {return report,errors.New("workspace is not a directory")}
    seen:=false
    add:=func(cmd,why,evidence string) {
        report.Candidates=append(report.Candidates,Candidate{Command:cmd,Purpose:why,Evidence:evidence,Verified:false})
    }

    raw,ok,err:=readFile(root,"package.json")
    if err!=nil {return report,fmt.Errorf("package.json: %w",err)}
    if ok {
        seen=true
        var pkg struct {
            Scripts map[string]json.RawMessage `json:"scripts"`
            PackageManager string `json:"packageManager"`
        }
        if err:=json.Unmarshal(raw,&pkg);err!=nil {return report,fmt.Errorf("invalid package.json: %w",err)}
        tool,warnings,err:=manager(root,pkg.PackageManager)
        if err!=nil {return report,fmt.Errorf("lockfiles: %w",err)}
        report.Warnings=append(report.Warnings,warnings...)
        names:=make([]string,0,len(pkg.Scripts))
        for name:=range pkg.Scripts {names=append(names,name)}
        sort.Strings(names)
        for _,name:=range names {
            why:=purpose(name)
            if why=="" {continue}
            if !safeName.MatchString(name) {report.Warnings=append(report.Warnings,"Skipped unsafe package.json script name.");continue}
            var body string
            if err:=json.Unmarshal(pkg.Scripts[name],&body);err!=nil {
                report.Warnings=append(report.Warnings,fmt.Sprintf("Skipped non-string script %q.",name))
                continue
            }
            if tool!="" {add(tool+" run "+name,why,"package.json scripts."+name)}
        }
    }

    for _,kind:=range []struct{name string; candidates [][2]string}{
        {"go.mod",[][2]string{{"go test ./...","test"},{"go build ./...","build"}}},
        {"Cargo.toml",[][2]string{{"cargo test","test"},{"cargo build","build"}}},
    } {
        _,ok,err:=readFile(root,kind.name)
        if err!=nil {return report,fmt.Errorf("%s: %w",kind.name,err)}
        if ok {
            seen=true
            for _,item:=range kind.candidates {add(item[0],item[1],kind.name)}
        }
    }
    contents,ok,err:=readFile(root,"Makefile")
    if err!=nil {return report,fmt.Errorf("Makefile: %w",err)}
    if ok {
        seen=true
        unique:=map[string]bool{}
        for _,match:=range targetPattern.FindAllStringSubmatch(string(contents),-1) {
            name:=match[1]
            if why:=purpose(name);why!="" && !unique[name] {
                add("make "+name,why,"Makefile target "+name)
                unique[name]=true
            }
        }
    }
    sort.Slice(report.Candidates,func(i,j int)bool {
        a,b:=report.Candidates[i],report.Candidates[j]
        if a.Purpose==b.Purpose {return a.Command<b.Command}
        return a.Purpose<b.Purpose
    })
    if seen {report.Status="discovered"}
    if seen && len(report.Candidates)==0 {report.Warnings=append(report.Warnings,"No supported commands found in the detected manifests.")}
    return report,nil
}

func run(args []string,stdout,stderr io.Writer) int {
    flags:=flag.NewFlagSet("devpilot-runbook",flag.ContinueOnError)
    flags.SetOutput(stderr)
    root:=flags.String("root",".","workspace to inspect")
    outputJSON:=flags.Bool("json",false,"emit JSON")
    if err:=flags.Parse(args);err!=nil {return 2}
    if flags.NArg()>0 {fmt.Fprintln(stderr,"unexpected arguments; use -root");return 2}
    report,err:=discover(*root)
    if err!=nil {fmt.Fprintln(stderr,"Inspection failed:",err);return 2}
    if *outputJSON {
        encoder:=json.NewEncoder(stdout)
        encoder.SetIndent("","  ")
        if err:=encoder.Encode(report);err!=nil {fmt.Fprintln(stderr,"Output failed:",err);return 2}
    } else {
        fmt.Fprintln(stdout,"DevPilot runbook — unverified suggestions; no commands executed")
        if report.Status=="no-manifest" {fmt.Fprintln(stdout,"No supported manifests found.")}
        for _,item:=range report.Candidates {
            fmt.Fprintf(stdout,"%-6s %-25s [%s]\n",item.Purpose,item.Command,item.Evidence)
        }
        for _,warning:=range report.Warnings {fmt.Fprintln(stdout,"Note:",warning)}
        fmt.Fprintln(stdout,"Review all project scripts before executing any command.")
    }
    return 0
}

func main() {os.Exit(run(os.Args[1:],os.Stdout,os.Stderr))}
