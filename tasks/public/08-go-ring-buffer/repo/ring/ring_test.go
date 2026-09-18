package ring_test

import (
	"testing"

	"example.com/ringbuf/ring"
)

func TestPushAndLen(t *testing.T) {
	r, err := ring.New(3)
	if err != nil {
		t.Fatal(err)
	}
	r.Push(1)
	r.Push(2)
	if r.Len() != 2 {
		t.Fatalf("want 2, got %d", r.Len())
	}
}
