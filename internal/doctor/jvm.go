package doctor

// jvmBuild is inferred from regular root-level build manifests only. Inspecting
// an untrusted project must not execute a wrapper script or follow symlinks.
type jvmBuild struct {
	Found    bool
	Tool     string
	Conflict bool
}

// discoverJVMBuild recognizes Maven and Gradle builds without reading or
// executing project-controlled files. Gradle settings files are also valid
// markers for multi-project roots without a root build.gradle file.
// Ambiguous mixed builds are reported instead of guessing which tool to run.
func discoverJVMBuild(root string) jvmBuild {
	maven := hasMarker(root, "pom.xml")
	gradle := hasMarker(root, "build.gradle") || hasMarker(root, "build.gradle.kts") ||
		hasMarker(root, "settings.gradle") || hasMarker(root, "settings.gradle.kts")
	switch {
	case maven && gradle:
		return jvmBuild{Found: true, Conflict: true}
	case maven:
		return jvmBuild{Found: true, Tool: "Maven"}
	case gradle:
		return jvmBuild{Found: true, Tool: "Gradle"}
	default:
		return jvmBuild{}
	}
}
