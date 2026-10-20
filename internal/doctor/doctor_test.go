package doctor
import (
    "os"
    "path/filepath"
    "strings"
    "testing"
)
func fixture(t *testing.T,files map[string]string)string{
    t.Helper();root:=t.TempDir()
    for name,content:=range files{if err:=os.WriteFile(filepath.Join(root,name),[]byte(content),0600);err!=nil{t.Fatal(err)}}
    return root
}
func hasCode(r Report,code string)bool{for _,f:=range r.Findings{if f.Code==code{return true}};return false}
func TestGoDetection(t *testing.T){
    r,err:=Analyze(fixture(t,map[string]string{"go.mod":"module sample\n\ngo 1.22\n"}))
    if err!=nil{t.Fatal(err)}
    if len(r.Languages)!=1||r.Languages[0]!="Go"{t.Fatalf("unexpected languages: %+v",r.Languages)}
    name,args,err:=TestCommand(r,"")
    if err!=nil||name!="go"||strings.Join(args," ")!="test ./..."{t.Fatalf("command %q %v: %v",name,args,err)}
}
func TestJavaScriptInvalidAndLockConflict(t *testing.T){
    r,err:=Analyze(fixture(t,map[string]string{"package.json":"{bad","package-lock.json":"{}","yarn.lock":""}))
    if err!=nil{t.Fatal(err)}
    if !hasCode(r,"manifest-invalid")||!hasCode(r,"multiple-lockfiles"){t.Fatalf("expected warnings, got %+v",r.Findings)}
    if len(r.TestRunners)!=0{t.Fatalf("invalid script should not produce runner: %v",r.TestRunners)}
}
func TestFrameworkAndNpmScript(t *testing.T){
    r,err:=Analyze(fixture(t,map[string]string{"package.json":`{"scripts":{"test":"vitest"},"dependencies":{"react":"*"}}`,"package-lock.json":"{}"}))
    if err!=nil{t.Fatal(err)}
    if len(r.Frameworks)!=1||r.Frameworks[0]!="react"{t.Fatalf("frameworks: %v",r.Frameworks)}
    name,_,err:=TestCommand(r,"")
    if name!="npm"||err!=nil{t.Fatalf("runner: %s %v",name,err)}
}
func TestMultipleRunnersRequireExplicitChoice(t *testing.T){
    r,err:=Analyze(fixture(t,map[string]string{"go.mod":"module x","package.json":`{"scripts":{"test":"echo ok"}}`}))
    if err!=nil{t.Fatal(err)}
    if _,_,err:=TestCommand(r,"");err==nil{t.Fatal("expected ambiguity error")}
    if _,_,err:=TestCommand(r,"cargo");err==nil{t.Fatal("unexpected undocumented runner")}
}
func TestEnvironmentNeverReadsSecretValues(t *testing.T){
    r,err:=Analyze(fixture(t,map[string]string{"go.mod":"module x",".env.example":"SECRET_KEY=placeholder\n# ignore\nexport OPTIONAL_TOKEN=\n",".env":"SECRET_KEY=topsecret"}))
    if err!=nil{t.Fatal(err)}
    for _,f:=range r.Findings{if strings.Contains(f.Message,"topsecret")||strings.Contains(f.Message,"placeholder"){t.Fatal("secret value leaked")}}
}
func TestManifestSymlinksIgnored(t *testing.T){
    root:=t.TempDir();outside:=filepath.Join(t.TempDir(),"package.json")
    if err:=os.WriteFile(outside,[]byte(`{"scripts":{"test":"echo unsafe"}}`),0600);err!=nil{t.Fatal(err)}
    if err:=os.Symlink(outside,filepath.Join(root,"package.json"));err!=nil{t.Skip("symlinks unavailable:",err)}
    r,err:=Analyze(root)
    if err!=nil{t.Fatal(err)}
    if !hasCode(r,"project-unrecognized")||len(r.TestRunners)!=0{t.Fatalf("symlink was followed: %+v",r)}
}
func TestInvalidWorkspace(t *testing.T){if _,err:=Analyze(filepath.Join(t.TempDir(),"missing"));err==nil{t.Fatal("expected error")}}
