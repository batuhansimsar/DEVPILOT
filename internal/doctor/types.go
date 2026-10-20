package doctor

// Report contains evidence from a read-only workspace inspection.
// It deliberately never contains values from local environment files.
type Report struct {
	Workspace    string       `json:"workspace"`
	Technologies []Technology `json:"technologies"`
	TestPlans    []TestPlan   `json:"testPlans"`
	Findings     []Finding    `json:"findings"`
	Git          GitInfo      `json:"git"`
	FilesScanned int          `json:"filesScanned"`
}

type Technology struct {
	Name     string `json:"name"`
	Evidence string `json:"evidence"`
}

type Finding struct {
	Severity string `json:"severity"` // info, warning, error
	Code     string `json:"code"`
	Message  string `json:"message"`
	Evidence string `json:"evidence,omitempty"`
	Remedy   string `json:"remedy,omitempty"`
}

type TestPlan struct {
	ID        string   `json:"id"`
	Directory string   `json:"directory"`
	Command   string   `json:"command"`
	Args      []string `json:"args"`
	Evidence  string   `json:"evidence"`
}

type GitInfo struct {
	Present      bool   `json:"present"`
	Status       string `json:"status"` // clean, modified, unknown, not-a-repository
	ChangedFiles int    `json:"changedFiles,omitempty"`
	Error        string `json:"error,omitempty"`
}
