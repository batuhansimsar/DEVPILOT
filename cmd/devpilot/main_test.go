package main

import (
 "bytes"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func TestTestCommandRequiresTrust(t *testing.T) {
 var out, errs bytes.Buffer
 if code := run([]string{"test"},&out,&errs); code!=2 { t.Fatalf("expected refusal, got %d",code) }
 if !strings.Contains(errs.String(),"--trust") { t.Fatal("missing trust warning") }
}
func TestDoctorJSON(t *testing.T) {
 root:=t.TempDir()
 if err:=os.WriteFile(filepath.Join(root,"go.mod"),[]byte("module example.com/demo\n"),0600); err!=nil { t.Fatal(err) }
 var out,errs bytes.Buffer
 if code:=run([]string{"doctor","--json",root},&out,&errs); code!=0 { t.Fatalf("exit %d: %s",code,errs.String()) }
 var doc struct { Root string `json:"root"`; Languages []string `json:"languages"` }
 if err:=json.Unmarshal(out.Bytes(),&doc); err!=nil { t.Fatal(err) }
 if doc.Root!=root || len(doc.Languages)!=1 || doc.Languages[0]!="Go" { t.Fatalf("report: %+v",doc) }
}
func TestUnknownCommand(t *testing.T) {
 var out,errs bytes.Buffer
 if run([]string{"nonsense"},&out,&errs)!=2 { t.Fatal("unknown command should exit 2") }
}
func TestInvalidTimeout(t *testing.T) {
 var out,errs bytes.Buffer
 if run([]string{"test","--trust","--timeout","0s"},&out,&errs)!=2 { t.Fatal("invalid timeout should fail") }
}
