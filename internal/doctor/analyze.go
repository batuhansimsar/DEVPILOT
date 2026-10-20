package doctor

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

const maxFiles = 12000
const maxDepth = 5
const maxManifestBytes = 1 << 20

var ignoredDirs = map[string]bool{
	".git": true, "node_modules": true, "vendor": true, ".venv": true,
	"venv": true, "dist": true, "build": true, ".next": true,
	"target": true, "bin": true, "obj": true, ".idea": true,
	".pytest_cache": true, "__pycache__": true,
}

var envKey = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)

type indexedFile struct {
	path string
	name string
	dir  string
}

// Analyze never executes code from the inspected workspace and does not
// traverse symbolic links, dependency folders, or arbitrary deep trees.
func Analyze(ctx context.Context, workspace string) (Report, error) {
	root, err := filepath.Abs(workspace)
	if err != nil { return Report{}, fmt.Errorf("resolve workspace: %w", err) }
	info, err := os.Lstat(root)
	if err != nil { return Report{}, fmt.Errorf("open workspace: %w", err) }
	if info.Mode() & os.ModeSymlink != 0 { return Report{}, errors.New("workspace must be a directory, not a symbolic link") }
	if !info.IsDir() { return Report{}, errors.New("workspace must be a directory") }

	r := Report{Workspace: root, Technologies: []Technology{}, TestPlans: []TestPlan{}, Findings: []Finding{}, Git: GitInfo{Status: "not-a-repository"}}
	var files []indexedFile
	limitReached := false
	walkErr := filepath.WalkDir(root, func(path string, entry fs.DirEntry, walkErr error) error {
		if ctx.Err() != nil { return ctx.Err() }
		if walkErr != nil {
			// Inaccessible entries must not be silently treated as absent.
			r.add("warning", "UNREADABLE_PATH", "Cannot inspect path", displayRel(root,path), "Check file permissions and rerun.")
			return nil
		}
		rel, _ := filepath.Rel(root, path)
		if rel == "." { return nil }
		depth := strings.Count(rel, string(filepath.Separator)) + 1
		if entry.IsDir() {
			if depth > maxDepth || ignoredDirs[entry.Name()] { return filepath.SkipDir }
			return nil
		}
		if !entry.Type().IsRegular() { return nil } // never follow symlinks
		if len(files) >= maxFiles { limitReached = true; return filepath.SkipAll }
		files = append(files, indexedFile{path: path, name: entry.Name(), dir: filepath.Dir(path)})
		return nil
	})
	if walkErr != nil { return r, fmt.Errorf("scan workspace: %w", walkErr) }
	r.FilesScanned = len(files)
	if limitReached { r.add("warning", "SCAN_LIMIT", "File scan stopped at the safety limit", "12000 files", "Run DevPilot from a smaller project root.") }

	// Sort before analysis to make JSON and terminal output deterministic.
	sort.Slice(files, func(i, j int) bool { return files[i].path < files[j].path })
	for _, f := range files {
		rel := displayRel(root, f.path)
		switch f.name {
		case "go.mod":
			r.tech("Go", rel)
			r.plan("go", root, f.dir, "go", []string{"test", "./..."}, rel)
		case "package.json":
			inspectPackageJSON(&r, root, f)
		case "pyproject.toml", "requirements.txt", "Pipfile":
			r.tech("Python", rel)
			if f.name == "pyproject.toml" { inspectPythonTests(&r, root, f) }
		case "pytest.ini":
			r.tech("Python", rel)
			r.plan("pytest", root, f.dir, "python3", []string{"-m", "pytest"}, rel)
		case "Cargo.toml":
			r.tech("Rust", rel)
			r.plan("cargo", root, f.dir, "cargo", []string{"test"}, rel)
		case "compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml":
			r.tech("Docker Compose", rel)
		case ".env.example", ".env.sample", ".env.template":
			inspectEnvTemplate(&r, root, f)
		}
		if strings.HasSuffix(f.name, ".csproj") || strings.HasSuffix(f.name, ".sln") || strings.HasSuffix(f.name, ".slnx") {
			r.tech(".NET", rel)
			if strings.Contains(strings.ToLower(f.name), "test") {
				r.plan("dotnet-"+f.name, root, f.dir, "dotnet", []string{"test", f.name}, rel)
			}
		}
	}
	for _, t := range r.Technologies {
		var binary string
		switch t.Name {
		case "Go": binary="go"
		case "Node.js": binary="node"
		case "Python": binary="python3"
		case "Rust": binary="cargo"
		case ".NET": binary="dotnet"
		default: continue
		}
		if _, err := exec.LookPath(binary); err != nil {
			r.add("warning", "TOOL_NOT_FOUND", fmt.Sprintf("%s executable is not on PATH", binary), t.Evidence, fmt.Sprintf("Install %s or configure PATH.", binary))
		}
	}
	if len(r.Technologies) == 0 {
		r.add("info", "NO_SUPPORTED_MANIFEST", "No supported project manifest found", "", "Try opening the project root containing a package manifest.")
	}
	if len(r.TestPlans) == 0 {
		r.add("info", "NO_TEST_COMMAND", "No confidently identifiable test command found", "", "Add a test configuration or run your project's documented test command.")
	}
	r.Git = inspectGit(ctx, root)
	if r.Git.Present && r.Git.Status == "unknown" {
		r.add("warning", "GIT_STATUS_UNAVAILABLE", "Could not inspect Git status", ".git", "Run git status manually to investigate.")
	}
	return r, nil
}

func displayRel(root, path string) string {
	rel, err := filepath.Rel(root,path)
	if err != nil { return filepath.Base(path) }
	return filepath.ToSlash(rel)
}

func (r *Report) tech(name, evidence string) {
	for _, t := range r.Technologies { if t.Name==name && t.Evidence==evidence {return} }
	r.Technologies=append(r.Technologies,Technology{Name:name,Evidence:evidence})
}

func (r *Report) add(severity, code, message, evidence, remedy string) {
	r.Findings=append(r.Findings,Finding{Severity:severity,Code:code,Message:message,Evidence:evidence,Remedy:remedy})
}

func (r *Report) plan(prefix, root, directory, command string, args []string, evidence string) {
	rel:=displayRel(root,directory)
	id:=prefix+":"+rel
	for _, p := range r.TestPlans {if p.ID==id{return}}
	r.TestPlans=append(r.TestPlans,TestPlan{ID:id,Directory:directory,Command:command,Args:args,Evidence:evidence})
}

func readSmallFile(path string) ([]byte,error) {
	info,err:=os.Lstat(path)
	if err!=nil{return nil,err}
	if !info.Mode().IsRegular() || info.Size()>maxManifestBytes {return nil,errors.New("manifest is not a regular file under 1 MiB")}
	return os.ReadFile(path)
}

func inspectPackageJSON(r *Report, root string, f indexedFile) {
	rel:=displayRel(root,f.path)
	r.tech("Node.js",rel)
	data,err:=readSmallFile(f.path)
	if err!=nil {r.add("warning","MANIFEST_UNREADABLE","Cannot read package manifest",rel,"Ensure the file is readable and smaller than 1 MiB.");return}
	var p struct {Scripts map[string]string `json:"scripts"`; Dependencies map[string]json.RawMessage `json:"dependencies"`; DevDependencies map[string]json.RawMessage `json:"devDependencies"`}
	if err=json.Unmarshal(data,&p);err!=nil {r.add("error","INVALID_PACKAGE_JSON","package.json is invalid JSON",rel,"Fix the JSON syntax.");return}
	for dep, framework := range map[string]string{"react":"React","next":"Next.js","vue":"Vue","vite":"Vite","@angular/core":"Angular","svelte":"Svelte"} {
		if _,ok:=p.Dependencies[dep];ok {r.tech(framework,rel+" dependency: "+dep)} else if _,ok:=p.DevDependencies[dep];ok {r.tech(framework,rel+" devDependency: "+dep)}
	}
	locks:=[]struct{name,runner string;args []string}{{"package-lock.json","npm",[]string{"test"}},{"npm-shrinkwrap.json","npm",[]string{"test"}},{"pnpm-lock.yaml","pnpm",[]string{"test"}},{"yarn.lock","yarn",[]string{"test"}},{"bun.lockb","bun",[]string{"test"}},{"bun.lock","bun",[]string{"test"}}}
	var found []string
	runner:="npm"
	for _, l:=range locks {if _,err:=os.Lstat(filepath.Join(f.dir,l.name));err==nil {found=append(found,l.name);runner=l.runner}}
	families:=map[string]bool{}
	for _, l:=range locks {for _, name:=range found {if l.name==name {families[l.runner]=true}}}
	if len(families)>1 {r.add("warning","MULTIPLE_LOCKFILES","Multiple package managers have lockfiles",strings.Join(found,", "),"Choose one package manager and remove stale lockfiles after review.")}
	if script,ok:=p.Scripts["test"];ok && strings.TrimSpace(script)!="" {
		if strings.Contains(script,"no test specified") {
			r.add("info","TEST_SCRIPT_PLACEHOLDER","Test script appears to be a placeholder",rel,"Replace it with a real test runner.")
		} else {
			r.plan("node",root,f.dir,runner,[]string{"test"},rel+" scripts.test")
			if _,err:=exec.LookPath(runner);err!=nil {r.add("warning","TOOL_NOT_FOUND",runner+" is not on PATH",rel,"Install the package manager or enable it using Corepack.")}
		}
	}
}

func inspectPythonTests(r *Report, root string, f indexedFile) {
	data,err:=readSmallFile(f.path)
	if err!=nil {return}
	// Recognize explicit pytest configuration, not arbitrary mentions in prose.
	if strings.Contains(string(data),"[tool.pytest") {
		r.plan("pytest",root,f.dir,"python3",[]string{"-m","pytest"},displayRel(root,f.path))
	}
}

func inspectEnvTemplate(r *Report, root string, f indexedFile) {
	rel:=displayRel(root,f.path)
	content,err:=readSmallFile(f.path)
	if err!=nil {r.add("warning","ENV_TEMPLATE_UNREADABLE","Cannot read environment template",rel,"Check template file permissions and size.");return}
	var keys []string
	seen:=map[string]bool{}
	for _,line:=range strings.Split(string(content),"\n") {
		line=strings.TrimSpace(line)
		line=strings.TrimPrefix(line,"export ")
		if strings.HasPrefix(line,"#") || !strings.Contains(line,"="){continue}
		key:=strings.TrimSpace(strings.SplitN(line,"=",2)[0])
		if envKey.MatchString(key) && !seen[key] {keys=append(keys,key);seen[key]=true}
	}
	if len(keys)>0 {
		r.add("info","ENV_KEYS_DISCOVERED",fmt.Sprintf("Environment template declares %d variable(s)",len(keys)),rel+": "+strings.Join(keys,", "),"Provide values through your environment or an untracked local .env file; never commit secrets.")
	}
	if _,err:=os.Stat(filepath.Join(f.dir,".env"));errors.Is(err,os.ErrNotExist) {
		r.add("info","LOCAL_ENV_ABSENT","No local .env file next to the environment template",rel,"If this project needs a .env file, create it locally; variables may instead be set externally.")
	}
}

func inspectGit(ctx context.Context, root string) GitInfo {
	result:=GitInfo{Status:"not-a-repository"}
	// Checking parent repositories would misreport a nested non-repository workspace.
	if _,err:=os.Lstat(filepath.Join(root,".git"));err!=nil {return result}
	result.Present=true
	result.Status="unknown"
	if _,err:=exec.LookPath("git");err!=nil {result.Error="git executable not found";return result}
	ctx, cancel:=context.WithTimeout(ctx,4*time.Second)
	defer cancel()
	cmd:=exec.CommandContext(ctx,"git","-C",root,"-c","core.fsmonitor=false","status","--porcelain=v1","--untracked-files=no")
	cmd.Env=append(os.Environ(),"GIT_OPTIONAL_LOCKS=0")
	out,err:=cmd.Output()
	if err!=nil {result.Error="git status failed or timed out";return result}
	trim:=strings.TrimSpace(string(out))
	if trim=="" {result.Status="clean";return result}
	result.Status="modified"
	result.ChangedFiles=len(strings.Split(trim,"\n"))
	return result
}
