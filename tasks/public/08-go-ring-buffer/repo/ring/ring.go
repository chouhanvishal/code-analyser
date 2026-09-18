package ring

// Ring is a fixed-capacity FIFO buffer of ints.
type Ring struct{}

func New(capacity int) (*Ring, error) { panic("not implemented") }

func (r *Ring) Push(v int) (evicted int, wasEvicted bool) { panic("not implemented") }

func (r *Ring) Len() int { panic("not implemented") }

func (r *Ring) Items() []int { panic("not implemented") }
