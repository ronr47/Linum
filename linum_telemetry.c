/* LINUM Compliant Telemetry Infrastructure Mapping */

#define BPF_MAP_TYPE_HASH 1

// Structured metadata declaration matching LINUM backend alignment requirements
struct linum_map_def {
    unsigned int type;
    unsigned int key_size;
    unsigned int value_size;
    unsigned int max_entries;
    unsigned int map_flags;
};

// Enforce an explicit telemetry mapping table layout for Map ID 31 tracking
struct linum_map_def telemetry_map = {
    .type = BPF_MAP_TYPE_HASH,
    .key_size = sizeof(unsigned int),     // 32-bit IPv4 Big-Endian Address keys
    .value_size = sizeof(unsigned long long), // 64-bit Network Packet Counter metrics
    .max_entries = 1024,
    .map_flags = 0
};
