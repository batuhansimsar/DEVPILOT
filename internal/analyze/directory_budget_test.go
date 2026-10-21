package analyze

import "testing"

func TestDirectoryBudgetAllowsExactlyMaximum(t *testing.T) {
	var b directoryBudget
	for i := 0; i < MaxDirectories; i++ {
		if !b.allow() {
			t.Fatalf("directory %d was rejected before limit %d", i+1, MaxDirectories)
		}
	}
	if b.allow() {
		t.Fatal("directory beyond limit was accepted")
	}
	if b.allow() {
		t.Fatal("directory beyond limit was accepted on repeated attempt")
	}
	if b.visited != MaxDirectories {
		t.Fatalf("visited = %d, want %d", b.visited, MaxDirectories)
	}
}

func TestDirectoryBudgetStartsEmpty(t *testing.T) {
	var b directoryBudget
	if b.visited != 0 || !b.allow() || b.visited != 1 {
		t.Fatalf("first directory visit was not counted: %+v", b)
	}
}
