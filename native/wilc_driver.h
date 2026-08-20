#ifndef WILC_DRIVER_H
#define WILC_DRIVER_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct CSpiVTable {
    void *context;
    void (*select)(void *ctx);
    void (*deselect)(void *ctx);
    void (*transfer_block)(void *ctx, const uint8_t *tx_buf, uint8_t *rx_buf, size_t len);
} CSpiVTable;

typedef struct CWilcDriver CWilcDriver;
typedef void (*CRxCallback)(void *ctx, const uint8_t *packet, size_t len);

int32_t wilc_driver_init(CWilcDriver *driver_mem, CSpiVTable spi_vtable);
int32_t wilc_initialize_transport(CWilcDriver *driver, uint8_t *out_mac);
int32_t wilc_transmit_frame(CWilcDriver *driver, const uint8_t *frame_ptr, size_t len);
void wilc_handle_interrupt(CWilcDriver *driver, CRxCallback rx_cb, void *cb_ctx);
void wilc_notify_irq(void);

#ifdef __cplusplus
}
#endif

#endif // WILC_DRIVER_H
