#ifndef BLE_H
#define BLE_H

#include <zephyr/kernel.h>
#include <zephyr/types.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <bluetooth/services/nus.h>
#include <dk_buttons_and_leds.h>
#include <zephyr/settings/settings.h>
#include <stdio.h>
#include <string.h>
#include <zephyr/logging/log.h>

#include <zephyr/bluetooth/conn.h> // Data length

#include <zephyr/bluetooth/hci.h>

#include <stdbool.h>
#include <stdint.h>
#include <zephyr/net_buf.h>
#include <zephyr/bluetooth/addr.h>
#include <zephyr/bluetooth/hci_types.h>

#define STACKSIZE CONFIG_BT_NUS_THREAD_STACK_SIZE
#define PRIORITY 7

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN (sizeof(DEVICE_NAME) - 1)

#define RUN_STATUS_LED DK_LED1
#define RUN_LED_BLINK_INTERVAL 1000

/* Function prototypes */
void ble_init(void);
void ble_send_thread(void* p1, void* p2);
void error(void);

#endif /* BLE_H */
