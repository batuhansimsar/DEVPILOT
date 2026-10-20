package main
import (
    "context"
    "encoding/json"
    "errors"
    "flag"
    "fmt"
    "os"
    "os/exec"
    "time"

    "github.com/batuhansimsar/DEVPILOT/internal/doctor"
)
func main(){os.Exit(run(os.Args[1:]))}
func run(args []string)int{
    if len(args)==0{usage();return 2}
    switch args[0]{
    case "doctor":
        flags:=flag.NewFlagSet("doctor",flag.ContinueOnError)
        path:=flags.String("path",".","project directory")
        jsonOutput:=flags.Bool("json",false,"machine-readable report")
        if err:=flags.Parse(args[1:]);err!=nil{return 2}
        if flags.NArg()!=0{fmt.Fprintln(os.Stderr,"unexpected positional arguments");return 2}
        report,err:=doctor.Analyze(*path)
        if err!=nil{fmt.Fprintln(os.Stderr,"doctor:",err);return 1}
        if *jsonOutput{
            encoder:=json.NewEncoder(os.Stdout);encoder.SetIndent("","  ")
            if err:=encoder.Encode(report);err!=nil{fmt.Fprintln(os.Stderr,err);return 1}
        }else{
            fmt.Println("DevPilot doctor:",report.Path)
            fmt.Println("Languages:",report.Languages)
            fmt.Println("Frameworks:",report.Frameworks)
            fmt.Println("Test runners:",report.TestRunners)
            for _,f:=range report.Findings{
                fmt.Printf("[%s] %s: %s\n",f.Level,f.Code,f.Message)
                if f.Remedy!=""{fmt.Println("  Next:",f.Remedy)}
            }
        }
        for _,f:=range report.Findings{if f.Level=="warning"{return 1}}
        return 0
    case "test":
        flags:=flag.NewFlagSet("test",flag.ContinueOnError)
        path:=flags.String("path",".","project directory")
        runner:=flags.String("runner","","choose a detected test runner")
        trust:=flags.Bool("trust",false,"allow execution of project-controlled test code")
        timeout:=flags.Duration("timeout",2*time.Minute,"test timeout (maximum 15m)")
        if err:=flags.Parse(args[1:]);err!=nil{return 2}
        if flags.NArg()!=0{fmt.Fprintln(os.Stderr,"unexpected positional arguments");return 2}
        if !*trust{fmt.Fprintln(os.Stderr,"refusing to run project code without --trust; inspect the repository first");return 2}
        if *timeout<=0||*timeout>15*time.Minute{fmt.Fprintln(os.Stderr,"timeout must be between 1ns and 15m");return 2}
        report,err:=doctor.Analyze(*path)
        if err!=nil{fmt.Fprintln(os.Stderr,err);return 1}
        name,cmdargs,err:=doctor.TestCommand(report,*runner)
        if err!=nil{fmt.Fprintln(os.Stderr,err);return 2}
        ctx,cancel:=context.WithTimeout(context.Background(),*timeout);defer cancel()
        cmd:=exec.CommandContext(ctx,name,cmdargs...)
        cmd.Dir=report.Path;cmd.Stdin=os.Stdin;cmd.Stdout=os.Stdout;cmd.Stderr=os.Stderr
        fmt.Fprintf(os.Stderr,"Running %s in %s (trusted workspace; timeout %s)\n",name,report.Path,*timeout)
        if err:=cmd.Run();err!=nil{
            if errors.Is(ctx.Err(),context.DeadlineExceeded){fmt.Fprintln(os.Stderr,"test timed out");return 124}
            fmt.Fprintln(os.Stderr,"test failed:",err);return 1
        }
        return 0
    case "help","--help","-h":usage();return 0
    default:fmt.Fprintln(os.Stderr,"unknown command:",args[0]);usage();return 2
    }
}
func usage(){fmt.Println("DevPilot — local developer project diagnostics\n\nCommands:\n  devpilot doctor [--path DIR] [--json]  inspect without executing project code\n  devpilot test --trust [--path DIR] [--runner NAME] [--timeout 2m]  run detected tests\n  devpilot help")}
