#ifndef PROOFBOOT_PB010_H
#define PROOFBOOT_PB010_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

uint32_t crc32(uint32_t buffer, uint32_t len);
uint32_t constant_time_eq(uint32_t a, uint32_t b, uint32_t len);
uint32_t parse_header(uint32_t slot_base);
uint32_t arbitrate_active_header(uint32_t dev);
uint32_t commit_transition(uint32_t dev, uint32_t new_payload, uint32_t payload_len, uint32_t new_generation);

#ifdef __cplusplus
}
#endif

#endif /* PROOFBOOT_PB010_H */
