// Package sarif converts DevPilot diagnostic findings into SARIF 2.1.0.
// Findings without precise file locations intentionally omit locations.
package sarif

import "sort"

// Finding is the small, presentation-independent part of a doctor finding.
type Finding struct {
	Level   string
	Code    string
	Message string
	Remedy  string
}

type Message struct {
	Text string `json:"text"`
}
type Rule struct {
	ID               string  `json:"id"`
	ShortDescription Message `json:"shortDescription"`
}
type Result struct {
	RuleID     string      `json:"ruleId"`
	Level      string      `json:"level"`
	Message    Message     `json:"message"`
	Properties *Properties `json:"properties,omitempty"`
}
type Properties struct {
	Remedy string `json:"remedy"`
}
type Driver struct {
	Name           string `json:"name"`
	InformationURI string `json:"informationUri"`
	Rules          []Rule `json:"rules"`
}
type Tool struct {
	Driver Driver `json:"driver"`
}
type Run struct {
	Tool    Tool     `json:"tool"`
	Results []Result `json:"results"`
}
type Log struct {
	Schema  string `json:"$schema"`
	Version string `json:"version"`
	Runs    []Run  `json:"runs"`
}

// Build renders observable non-pass findings using deterministic rule order.
// No source locations are guessed: GitHub code scanning requires real locations
// to display per-file alerts, so this output is meant for general SARIF consumers
// until the doctor engine records grounded source paths/lines.
func Build(findings []Finding) Log {
	rules := map[string]struct{}{}
	results := []Result{}
	for _, f := range findings {
		if f.Code == "" || f.Message == "" {
			continue
		}
		level := ""
		switch f.Level {
		case "warning":
			level = "warning"
		case "error":
			level = "error"
		case "info":
			level = "note"
		default:
			continue // Exclude pass and unknown states.
		}
		rules[f.Code] = struct{}{}
		r := Result{RuleID: f.Code, Level: level, Message: Message{Text: f.Message}}
		if f.Remedy != "" {
			r.Properties = &Properties{Remedy: f.Remedy}
		}
		results = append(results, r)
	}
	codes := make([]string, 0, len(rules))
	for code := range rules {
		codes = append(codes, code)
	}
	sort.Strings(codes)
	outRules := make([]Rule, 0, len(codes))
	for _, code := range codes {
		outRules = append(outRules, Rule{ID: code, ShortDescription: Message{Text: code}})
	}
	return Log{
		Schema: "https://json.schemastore.org/sarif-2.1.0.json", Version: "2.1.0",
		Runs: []Run{{Tool: Tool{Driver: Driver{Name: "DevPilot", InformationURI: "https://github.com/batuhansimsar/DEVPILOT", Rules: outRules}}, Results: results}},
	}
}
