package doctor

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func put(t *testing.T, root, relative, contents string) {
	t.Helper()
	path := filepath.Join(root, relative)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil { t.Fatal(err) }
	if err := os.WriteFile(path, []byte(contents), 0644); err != nil { t.Fatal(err) }
}
func hasFinding(r Report, code string) bool {
	for _, f := range r.Findings { if f.Code == code {return true} }
	return false
}
func hasTechnology(r Report, name string) bool {
	for _, t := range r.Technologies { if t.Name == name {return true} }
	return false
}

func TestAnalyzeNodeAndEnvDoesNotLeakValues(t *testing.T) {
	root := t.TempDir()
	put(t,root,"package.json",`{"dependencies":{"react":"^18.0.0"},"scripts":{"test":"vitest run"}}`)
	put(t,root,"package-lock.json",`{}`)
	put(t,root,".env.example","# explanation\nAPI_KEY=do-not-print-this\nexport API_URL=https://invalid.example\nBAD KEY=ignored\n")
	put(t,root,".env","API_KEY=real-private-secret")
	r,err:=Analyze(context.Background(),root)
	if err!=nil {t.Fatal(err)}
	if !hasTechnology(r,"React") || !hasTechnology(r,"Node.js") {t.Fatalf("tech missing: %#v",r.Technologies)}
	if len(r.TestPlans)!=1 || r.TestPlans[0].Command!="npm" {t.Fatalf("unexpected plan: %#v",r.TestPlans)}
	if !hasFinding(r,"ENV_KEYS_DISCOVERED") {t.Fatalf("missing env finding: %#v",r.Findings)}
	if hasFinding(r,"LOCAL_ENV_ABSENT") {t.Fatal(".env exists")}
	for _,f:=range r.Findings {
		if strings.Contains(f.Evidence,"do-not-print-this") || strings.Contains(f.Evidence,"real-private-secret") {t.Fatal("env value leaked")}
	}
}

func TestBrokenManifestAndConflictingLockfiles(t *testing.T) {
	root:=t.TempDir()
	put(t,root,"package.json",`{"scripts":`)
	put(t,root,"pnpm-lock.yaml","")
	r,err:=Analyze(context.Background(),root)
	if err!=nil {t.Fatal(err)}
	if !hasFinding(r,"INVALID_PACKAGE_JSON") {t.Fatalf("expected error: %#v",r.Findings)}
	put(t,root,"package.json",`{"scripts":{"test":"jest"}}`)
	put(t,root,"yarn.lock","")
	r,err=Analyze(context.Background(),root)
	if err!=nil {t.Fatal(err)}
	if !hasFinding(r,"MULTIPLE_LOCKFILES") {t.Fatalf("expected conflict: %#v",r.Findings)}
}

func TestIgnoresDependencyFoldersAndSymlinks(t *testing.T) {
	root:=t.TempDir()
	put(t,root,"go.mod","module example.com/fixture\n\ngo 1.22\n")
	put(t,root,"node_modules/fake/package.json",`{"scripts":{"test":"evil"}}`)
	outside:=t.TempDir()
	put(t,outside,"package.json",`{"scripts":{"test":"evil"}}`)
	if err:=os.Symlink(outside,filepath.Join(root,"link"));err!=nil {t.Skipf("symlink not permitted: %v",err)}
	r,err:=Analyze(context.Background(),root)
	if err!=nil {t.Fatal(err)}
	if hasTechnology(r,"Node.js") || len(r.TestPlans)!=1 || r.TestPlans[0].Command!="go" {t.Fatalf("followed unsafe content: %#v",r)}
	_,err=Analyze(context.Background(),filepath.Join(root,"link"))
	if err==nil {t.Fatal("symlink workspace should be rejected")}
}

func TestEmptyWorkspaceIsNonFatal(t *testing.T) {
	r,err:=Analyze(context.Background(),t.TempDir())
	if err!=nil {t.Fatal(err)}
	if !hasFinding(r,"NO_SUPPORTED_MANIFEST") || !hasFinding(r,"NO_TEST_COMMAND") {t.Fatalf("missing findings: %#v",r.Findings)}
	if r.Git.Status!="not-a-repository" {t.Fatalf("wrong git info: %#v",r.Git)}
}

func TestPlaceholderScriptNotRunnable(t *testing.T) {
	root:=t.TempDir()
	put(t,root,"package.json",`{"scripts":{"test":"echo Error: no test specified && exit 1"}}`)
	r,err:=Analyze(context.Background(),root)
	if err!=nil {t.Fatal(err)}
	if len(r.TestPlans)!=0 || !hasFinding(r,"TEST_SCRIPT_PLACEHOLDER") {t.Fatalf("unexpected plan: %#v",r)}
}

func TestCancellation(t *testing.T) {
	ctx,cancel:=context.WithCancel(context.Background());cancel()
	_,err:=Analyze(ctx,t.TempDir())
	if err==nil {t.Fatal("expected cancellation")}
}

func TestTwoDotnetProjectsGetDistinctPlans(t *testing.T) {
	root:=t.TempDir()
	put(t,root,"Alpha.Tests.csproj","<Project Sdk=\"Microsoft.NET.Sdk\" />")
	put(t,root,"Beta.Tests.csproj","<Project Sdk=\"Microsoft.NET.Sdk\" />")
	r,err:=Analyze(context.Background(),root)
	if err!=nil {t.Fatal(err)}
	if len(r.TestPlans)!=2 || r.TestPlans[0].ID==r.TestPlans[1].ID {t.Fatalf("distinct test plans expected: %#v",r.TestPlans)}
}
