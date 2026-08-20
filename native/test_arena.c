#include <assert.h>
#include <unistd.h>
#include "vortex_engine.c" // Conceptual single-source build target

int main() {
    MemoryArena arena = initialize_arena();
    assert(arena.execution_runway != NULL);
    assert(((uintptr_t)arena.execution_runway % sysconf(_SC_PAGESIZE)) == 0);
    return 0;
}
