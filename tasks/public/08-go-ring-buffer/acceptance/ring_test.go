package acceptance

import (
	"reflect"
	"testing"

	"example.com/ringbuf/ring"
)

func TestNewValidation(t *testing.T) {
	for _, c := range []int{0, -1} {
		if _, err := ring.New(c); err == nil {
			t.Errorf("capacity %d: want error", c)
		}
	}
}

func TestEvictionOrder(t *testing.T) {
	r, _ := ring.New(3)
	for _, v := range []int{1, 2, 3} {
		if _, ev := r.Push(v); ev {
			t.Fatalf("unexpected eviction on %d", v)
		}
	}
	old, ev := r.Push(4)
	if !ev || old != 1 {
		t.Fatalf("want evicted 1,true got %d,%v", old, ev)
	}
	old, ev = r.Push(5)
	if !ev || old != 2 {
		t.Fatalf("want evicted 2,true got %d,%v", old, ev)
	}
	if got := r.Items(); !reflect.DeepEqual(got, []int{3, 4, 5}) {
		t.Fatalf("items %v", got)
	}
	if r.Len() != 3 {
		t.Fatalf("len %d", r.Len())
	}
}

func TestItemsIsCopy(t *testing.T) {
	r, _ := ring.New(2)
	r.Push(7)
	items := r.Items()
	items[0] = 99
	if r.Items()[0] != 7 {
		t.Fatal("Items must return a copy")
	}
}

func TestEmpty(t *testing.T) {
	r, _ := ring.New(1)
	if r.Len() != 0 || len(r.Items()) != 0 {
		t.Fatal("new ring must be empty")
	}
}

func TestCapacityOne(t *testing.T) {
	r, _ := ring.New(1)
	r.Push(1)
	old, ev := r.Push(2)
	if !ev || old != 1 || r.Items()[0] != 2 {
		t.Fatal("capacity-one ring misbehaves")
	}
}
