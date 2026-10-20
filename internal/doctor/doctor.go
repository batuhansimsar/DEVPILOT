// Package doctor inspects a workspace without running project code.
package doctor

import (
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "os/exec"
 "path/filepath"
 "regexp"
 "sort"
 "strings"
 "time"
)

const maxFileBytes int64 = 1024 * 1024

type Finding struct {
 Severity string `json:"severity"`
 Code string `json:"code"`
 Message string `json:"message"`
 Evidence string `json:"evidence,omitempty"`
 Remedy string `json:"remedy,omitempty"`
}

type Report struct {
 Root string `json:"root"`
 Languages []string `json:"languages"`
 Frameworks []string `json:"frameworks"`
 PackageManagers []string `json:"package_managers"`
 TestCommands map[string][]string `json:"test_commands"`
 Findings []Finding `json:"findings"`
}

type packageJSON struct {
 Scripts map[string]string `json:"scripts"`
 Dependencies map[string]string `json:"dependencies"`
 DevDependencies map[string]string `json:"devDependencies"`
}

func addUnique(xs []string, v string) []string {
 for _, x := range xs { if x == v { return xs } }
 return append(xs, v)
}
func (r *Report) finding(severity, code, msg, evidence, remedy string) {
 r.Findings = append(r.Findings, Finding{severity, code, msg, evidence, remedy})
}

func ResolveRoot(path string) (string, error) {
 if path == "" { path = "." }
 abs, err := filepath.Abs(path)
 if err != nil { return "", fmt.Errorf("resolve workspace: %w",err) }
 root, err := filepath.EvalSymlinks(abs)
 if err != nil { return "", fmt.Errorf("resolve workspace: %w",err) }
 stat, err := os.Stat(root)
 if err != nil { return "", fmt.Errorf("inspect workspace: %w",err) }
 if !stat.IsDir() { return "", fmt.Errorf("workspace is not a directory: %s",root) }
 return root,nil
}

// Inspect reads bounded root-level metadata. No dependency, test or build scripts run.
func Inspect(ctx context.Context, path string) (Report,error) {
 root,err := ResolveRoot(path)
 if err != nil { return Report{},err }
 r := Report{Root:root, Languages:[]string{}, Frameworks:[]string{}, PackageManagers:[]string{}, TestCommands:map[string][]string{}, Findings:[]Finding{}}
 exists := func(name string) bool { return regularFile(&r,root,name) }
 if exists("go.mod") {
  r.Languages=addUnique(r.Languages,"Go")
  r.TestCommands["go"]=[]string{"go","test","./..."}
  r.finding("info","go-module","Go module detected","go.mod","Run go test ./... after reviewing and trusting the repository.")
  executable(&r,"go","Go toolchain")
 }
 if exists("package.json") {
  r.Languages=addUnique(r.Languages,"JavaScript/TypeScript")
  detectNode(&r,root)
  executable(&r,"node","Node.js runtime")
 }
 if exists("pyproject.toml") || exists("requirements.txt") || exists("Pipfile") {
  r.Languages=addUnique(r.Languages,"Python")
  if exists("pytest.ini") || exists("conftest.py") || hasPytestConfig(root) {
   r.TestCommands["python"]=[]string{pythonExecutable(),"-m","pytest"}
   r.finding("info","pytest-detected","pytest configuration detected","pytest.ini, conftest.py or pyproject.toml","Review tests before devpilot test --trust --runner python.")
  }
  if _,err:=exec.LookPath(pythonExecutable()); err!=nil { r.finding("warn","python-unavailable","Python interpreter not found in PATH","Python manifest found","Install Python and add it to PATH.") }
 }
 if exists("Cargo.toml") {
  r.Languages=addUnique(r.Languages,"Rust")
  r.TestCommands["rust"]=[]string{"cargo","test"}
  executable(&r,"cargo","Rust Cargo toolchain")
 }
 entries,err:=os.ReadDir(root)
 if err!=nil { return Report{},fmt.Errorf("read workspace: %w",err) }
 for _,e:=range entries {
  name:=e.Name()
  if e.Type().IsRegular() && (strings.HasSuffix(name,".sln") || strings.HasSuffix(name,".csproj")) {
   r.Languages=addUnique(r.Languages,"C#/.NET")
   r.TestCommands["dotnet"]=[]string{"dotnet","test"}
   executable(&r,"dotnet",".NET SDK")
   break
  }
 }
 inspectEnv(&r,root)
 inspectGit(ctx,&r,root)
 if len(r.Languages)==0 { r.finding("warn","unknown-project","No supported project manifest found at workspace root","Checked go.mod, package.json, Python manifests, Cargo.toml and root-level .NET projects","Point DevPilot at a root with a recognized manifest.") }
 sort.Strings(r.Languages); sort.Strings(r.Frameworks); sort.Strings(r.PackageManagers)
 return r,nil
}

// Refuse symlinks/special files; ignore missing optional manifests.
func regularFile(r *Report,root,name string) bool {
 info,err:=os.Lstat(filepath.Join(root,name))
 if errors.Is(err,os.ErrNotExist) { return false }
 if err!=nil { r.finding("warn","file-inaccessible","Could not inspect a project file",name,"Check permissions."); return false }
 if info.Mode()&os.ModeSymlink!=0 { r.finding("warn","symlink-skipped","Manifest symlink ignored for safety",name,"Inspect the link target manually."); return false }
 return info.Mode().IsRegular()
}

func readLimited(root,name string) ([]byte,error) {
 info,err:=os.Lstat(filepath.Join(root,name))
 if err!=nil { return nil,err }
 if !info.Mode().IsRegular() { return nil,fmt.Errorf("not a regular file: %s",name) }
 if info.Size()>maxFileBytes { return nil,fmt.Errorf("%s exceeds 1 MiB limit",name) }
 f,err:=os.Open(filepath.Join(root,name))
 if err!=nil { return nil,err }
 defer f.Close()
 data,err:=io.ReadAll(io.LimitReader(f,maxFileBytes+1))
 if err!=nil { return nil,err }
 if int64(len(data))>maxFileBytes { return nil,fmt.Errorf("%s exceeds 1 MiB limit",name) }
 return data,nil
}

func detectNode(r *Report,root string) {
 data,err:=readLimited(root,"package.json")
 if err!=nil { r.finding("warn","package-json-unreadable","Cannot read package.json","package.json","Ensure file is regular, readable and under 1 MiB."); return }
 var p packageJSON
 if err:=json.Unmarshal(data,&p); err!=nil { r.finding("warn","package-json-invalid","Invalid package.json","JSON parsing failed","Correct package.json syntax."); return }
 deps:=map[string]bool{}
 for k:=range p.Dependencies { deps[k]=true }
 for k:=range p.DevDependencies { deps[k]=true }
 for name,label:=range map[string]string{"react":"React","next":"Next.js","vue":"Vue","@angular/core":"Angular","express":"Express","vite":"Vite","svelte":"Svelte","@nestjs/core":"NestJS"} {
  if deps[name] { r.Frameworks=addUnique(r.Frameworks,label) }
 }
 locks:=[]struct{name,manager string}{
  {"package-lock.json","npm"},{"npm-shrinkwrap.json","npm"},{"pnpm-lock.yaml","pnpm"},
  {"yarn.lock","yarn"},{"bun.lock","bun"},{"bun.lockb","bun"},
 }
 lockNames:=[]string{}
 for _,l:=range locks {
  if regularFile(r,root,l.name) { r.PackageManagers=addUnique(r.PackageManagers,l.manager); lockNames=append(lockNames,l.name) }
 }
 if len(r.PackageManagers)>1 { r.finding("warn","lockfile-conflict","Multiple package managers have lockfiles",strings.Join(lockNames,", "),"Keep only the selected package manager lockfile.") }
 if len(r.PackageManagers)==0 {
  r.PackageManagers=append(r.PackageManagers,"npm")
  r.finding("info","no-node-lockfile","No recognized Node lockfile found; npm is an unverified fallback","package.json","Commit a package manager lockfile for reproducibility.")
 }
 manager:=r.PackageManagers[0]
 if len(r.PackageManagers)==1 { executable(r,manager,"Node package manager") }
 if script,ok:=p.Scripts["test"]; ok && strings.TrimSpace(script)!="" && !placeholderTest(script) {
  switch manager {
  case "yarn": r.TestCommands["node"]=[]string{"yarn","test"}
  case "pnpm": r.TestCommands["node"]=[]string{"pnpm","test"}
  case "bun": r.TestCommands["node"]=[]string{"bun","run","test"}
  default: r.TestCommands["node"]=[]string{"npm","test"}
  }
  r.finding("info","node-tests","Project test script is available (not executed)","package.json scripts.test","Review its content before devpilot test --trust --runner node.")
 } else {
  r.finding("info","node-tests-missing","No runnable test script detected","package.json scripts.test","Add a meaningful test script.")
 }
}

func placeholderTest(script string) bool {
 s:=strings.ToLower(script)
 return strings.Contains(s,"no test specified") || strings.Contains(s,"no tests specified")
}
func executable(r *Report,name,description string) {
 if _,err:=exec.LookPath(name); err!=nil { r.finding("warn","tool-unavailable",description+" not found in PATH",name,"Install the toolchain or add it to PATH.") }
}
func pythonExecutable() string {
 if _,err:=exec.LookPath("python3"); err==nil { return "python3" }
 return "python"
}
func hasPytestConfig(root string) bool {
 data,err:=readLimited(root,"pyproject.toml")
 return err==nil && strings.Contains(string(data),"[tool.pytest")
}

var envName=regexp.MustCompile("^[A-Za-z_][A-Za-z0-9_]*$")
func parseEnvKeys(data []byte) map[string]bool {
 out:=map[string]bool{}
 for _,line:=range strings.Split(string(data),"\n") {
  line=strings.TrimSpace(line)
  if strings.HasPrefix(line,"#") || line=="" { continue }
  line=strings.TrimPrefix(line,"export ")
  key,_,ok:=strings.Cut(line,"=")
  if ok && envName.MatchString(strings.TrimSpace(key)) { out[strings.TrimSpace(key)]=true }
 }
 return out
}
func inspectEnv(r *Report,root string) {
 expected:=map[string]bool{}
 found:=[]string{}
 for _,file:=range []string{".env.example",".env.sample",".env.template"} {
  if !regularFile(r,root,file) { continue }
  data,err:=readLimited(root,file)
  if err!=nil { r.finding("warn","env-example-unreadable","Cannot inspect environment example",file,"Ensure file is readable and below 1 MiB."); continue }
  found=append(found,file)
  for k:=range parseEnvKeys(data) { expected[k]=true }
 }
 if len(found)==0 { return }
 configured:=map[string]bool{}
 for _,file:=range []string{".env",".env.local"} {
  if !regularFile(r,root,file) { continue }
  data,err:=readLimited(root,file)
  if err!=nil { r.finding("warn","env-unreadable","Could not inspect local environment file",file,"Check permissions and size."); continue }
  for k:=range parseEnvKeys(data) { configured[k]=true }
 }
 missing:=[]string{}
 for key:=range expected { _,set:=os.LookupEnv(key); if !set && !configured[key] { missing=append(missing,key) } }
 sort.Strings(missing)
 if len(missing)>0 {
  r.finding("warn","env-keys-unconfigured",fmt.Sprintf("%d example environment keys have no local entry",len(missing)),strings.Join(missing,", "),"Set keys in the environment or local .env; some may be optional. Never commit secrets.")
 } else {
  r.finding("info","env-keys-present","All example environment keys have local entries; values not validated",strings.Join(found,", "),"Verify credentials and connectivity separately.")
 }
}

func inspectGit(ctx context.Context,r *Report,root string) {
 if _,err:=os.Lstat(filepath.Join(root,".git")); err!=nil {
  r.finding("info","git-not-detected","No .git metadata found at workspace root",".git missing","Initialize Git if version control is desired."); return
 }
 if _,err:=exec.LookPath("git"); err!=nil {
  r.finding("warn","git-unavailable","Git metadata exists but git is not in PATH",".git","Install Git."); return
 }
 c,cancel:=context.WithTimeout(ctx,3*time.Second); defer cancel()
 cmd:=exec.CommandContext(c,"git","-C",root,"-c","core.fsmonitor=false","-c","core.untrackedCache=false","status","--porcelain=v1","-uno")
 cmd.Env=append(os.Environ(),"GIT_OPTIONAL_LOCKS=0","GIT_TERMINAL_PROMPT=0")
 out,err:=cmd.Output()
 if err!=nil { r.finding("warn","git-inspection-failed","Unable to inspect Git working tree",".git","Run git status manually; check workspace trust."); return }
 if len(out)==0 {
  r.finding("info","git-clean-tracked","Tracked Git files have no pending changes","git status --porcelain=v1 -uno","Untracked files intentionally omitted.")
 } else {
  r.finding("info","git-modified","Tracked Git files contain pending changes","git status --porcelain=v1 -uno","Review changes with git status.")
 }
}
