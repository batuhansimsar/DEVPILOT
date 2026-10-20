package doctor

import (
 "context"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func put(t *testing.T,root,name,value string) {
 t.Helper()
 if err:=os.WriteFile(filepath.Join(root,name),[]byte(value),0600); err!=nil { t.Fatal(err) }
}
func hasFinding(r Report, code string) bool {
 for _,f:=range r.Findings { if f.Code==code { return true } }
 return false
}
func TestNodeProjectDetectionAndFrameworks(t *testing.T) {
 root:=t.TempDir()
 put(t,root,"package.json",`{"scripts":{"test":"vitest run"},"dependencies":{"react":"*","next":"*"}}`)
 put(t,root,"pnpm-lock.yaml","lockfileVersion: '9.0'\n")
 r,err:=Inspect(context.Background(),root)
 if err!=nil { t.Fatal(err) }
 if len(r.Frameworks)!=2 || r.Frameworks[0]!="Next.js" || r.Frameworks[1]!="React" { t.Fatalf("frameworks: %v",r.Frameworks) }
 if len(r.PackageManagers)!=1 || r.PackageManagers[0]!="pnpm" { t.Fatalf("package managers: %v",r.PackageManagers) }
 if got:=strings.Join(r.TestCommands["node"]," "); got!="pnpm test" { t.Fatalf("wrong test command: %s",got) }
}
func TestLockfileConflict(t *testing.T) {
 root:=t.TempDir()
 put(t,root,"package.json",`{"scripts":{"test":"vitest"}}`)
 put(t,root,"yarn.lock","")
 put(t,root,"package-lock.json","{}")
 r,err:=Inspect(context.Background(),root)
 if err!=nil { t.Fatal(err) }
 if !hasFinding(r,"lockfile-conflict") { t.Fatal("expected conflicting lockfiles warning") }
}
func TestInvalidPackageJSON(t *testing.T) {
 root:=t.TempDir()
 put(t,root,"package.json","this is not json")
 r,err:=Inspect(context.Background(),root)
 if err!=nil { t.Fatal(err) }
 if !hasFinding(r,"package-json-invalid") { t.Fatal("invalid JSON not detected") }
 if len(r.TestCommands)!=0 { t.Fatalf("unexpected tests: %v",r.TestCommands) }
}
func TestEnvRedactsValues(t *testing.T) {
 t.Setenv("DPLT_TEST_MISSING_123","")
 root:=t.TempDir()
 secret:="super-secret-value-do-not-print"
 put(t,root,".env.example","TOKEN="+secret+"\nDPLT_TEST_MISSING_123=abc\n")
 put(t,root,".env","TOKEN="+secret+"\n")
 r,err:=Inspect(context.Background(),root)
 if err!=nil { t.Fatal(err) }
 data,err:=json.Marshal(r)
 if err!=nil { t.Fatal(err) }
 if strings.Contains(string(data),secret) { t.Fatal("secret value leaked in report") }
 if !hasFinding(r,"env-keys-present") { t.Fatal("environment entries not recognized") }
}
func TestUnconfiguredEnvKeys(t *testing.T) {
 root:=t.TempDir()
 put(t,root,".env.example","DPLT_TEST_MISSING_UNLIKELY_KEY_9823=secret\n")
 r,err:=Inspect(context.Background(),root)
 if err!=nil { t.Fatal(err) }
 if !hasFinding(r,"env-keys-unconfigured") { t.Fatal("expected missing env key warning") }
}
func TestSymlinkIsSkipped(t *testing.T) {
 root:=t.TempDir()
 elsewhere:=t.TempDir()
 put(t,elsewhere,"package.json",`{"scripts":{"test":"evil"}}`)
 if err:=os.Symlink(filepath.Join(elsewhere,"package.json"),filepath.Join(root,"package.json")); err!=nil { t.Skipf("symlinks unsupported: %v",err) }
 r,err:=Inspect(context.Background(),root)
 if err!=nil { t.Fatal(err) }
 if !hasFinding(r,"symlink-skipped") { t.Fatal("expected symlink warning") }
 if _,ok:=r.TestCommands["node"]; ok { t.Fatal("unexpected test from symlink") }
}
func TestOversizeManifest(t *testing.T) {
 root:=t.TempDir()
 put(t,root,"package.json",strings.Repeat("X",int(maxFileBytes)+1))
 r,err:=Inspect(context.Background(),root)
 if err!=nil { t.Fatal(err) }
 if !hasFinding(r,"package-json-unreadable") { t.Fatal("expected oversize warning") }
}
func TestNoManifest(t *testing.T) {
 r,err:=Inspect(context.Background(),t.TempDir())
 if err!=nil { t.Fatal(err) }
 if !hasFinding(r,"unknown-project") { t.Fatal("expected unknown project finding") }
}
func TestPlaceholderTestScriptIgnored(t *testing.T) {
 root:=t.TempDir()
 put(t,root,"package.json",`{"scripts":{"test":"echo Error: no test specified && exit 1"}}`)
 r,err:=Inspect(context.Background(),root)
 if err!=nil { t.Fatal(err) }
 if _,ok:=r.TestCommands["node"]; ok { t.Fatal("placeholder must not be runnable") }
}
func TestGoAndRust(t *testing.T) {
 root:=t.TempDir()
 put(t,root,"go.mod","module example.com/example\n")
 put(t,root,"Cargo.toml","[package]\nname = \"example\"\n")
 r,err:=Inspect(context.Background(),root)
 if err!=nil { t.Fatal(err) }
 if len(r.TestCommands)!=2 { t.Fatalf("expected two test runners, got %v",r.TestCommands) }
}
