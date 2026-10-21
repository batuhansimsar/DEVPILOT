package doctor

import (
	"os"
	"path/filepath"
)

// goProjectMarkers recognizes either a Go module or a workspace at the root.
// Lstat prevents symlinked files (which may point outside the workspace) from
// affecting project detection, consistent with other doctor marker checks.
func goProjectMarkers(root string) (module, workspace bool) {
	isRegular := func(name string) bool {
		info, err := os.Lstat(filepath.Join(root, name))
		return err == nil && info.Mode().IsRegular()
	}
	return isRegular("go.mod"), isRegular("go.work")
}
