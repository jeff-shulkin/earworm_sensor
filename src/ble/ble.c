/*
    The main points that need to be set (or confirmed) are:
    Peripheral connection
    2 Mbps PHY layer
    0 dBm transmit power
    Using an external LF crystal oscillator
    Enabling Data Packet Length Extension
    Enabling Connection Event Length Extension
 */


#include "../../include/ble.h"

#define LOG_MODULE_NAME peripheral_uart
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static K_SEM_DEFINE(ble_init_ok, 0, 1);
extern struct k_sem poll_buffer;
extern struct k_fifo fifo;
static struct bt_conn *current_conn;

static const struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, DEVICE_NAME_LEN),
};

static const struct bt_data sd[] = {
    BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_NUS_VAL),
};

/* Callback when a device connects */
static void connected(struct bt_conn *conn, uint8_t err)
{
    char addr[BT_ADDR_LE_STR_LEN];

    if (err) {
        printk("Connection failed, err 0x%02x\n", err);
        return;
    }

    bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));
    printk("Connected: %s\n", addr);

    if (!current_conn) {
        current_conn = bt_conn_ref(conn);
    }

    dk_set_led_on(DK_LED2); // LED

    /* Request 2 Mbps PHY */
    err = bt_conn_le_phy_update(conn, BT_CONN_LE_PHY_PARAM_2M);
    if (err) {
        printk("PHY update failed (err %d)", err);
    } else {
        printk("PHY update requested: 2 Mbps\n");
    }

    /* Enable DLE */
    struct bt_conn_le_data_len_param data_len = {
        .tx_max_len = 251,
        .tx_max_time = 2120,
    };

    err = bt_conn_le_data_len_update(conn, &data_len);
    if (err) {
        printk("Data Length Extension update failed (err %d)\n", err);
    } else {
        printk("DLE update successful\n");
    }

    /* Set Connection Interval to 2000 ms */
    struct bt_le_conn_param conn_param = {
        .interval_min = 1600,  // 2000 ms / 1.25 ms = 1600
        .interval_max = 1600,
        .latency = 0,
        .timeout = 400,  // 4 seconds
    };

    err = bt_conn_le_param_update(conn, &conn_param);
    if (err) {
        printk("Connection param update failed (err %d)\n", err);
    } else {
        printk("Connection params updated\n");
    }
}

/* Callback when a device disconnects */
static void disconnected(struct bt_conn *conn, uint8_t reason)
{
    char addr[BT_ADDR_LE_STR_LEN];

    bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));
    printk("Disconnected: %s, reason 0x%02x\n", addr, reason);

    if (current_conn) {
        bt_conn_unref(current_conn);
        current_conn = NULL;
        dk_set_led_off(DK_LED2);
    }
}

/* Register Bluetooth connection callbacks */
BT_CONN_CB_DEFINE(conn_callbacks) = {
    .connected = connected,
    .disconnected = disconnected,
};

/* Callback when receiving data over Bluetooth */
static void bt_receive_cb(struct bt_conn *conn, const uint8_t *const data, uint16_t len)
{
    char addr[BT_ADDR_LE_STR_LEN] = {0};
    bt_addr_le_to_str(bt_conn_get_dst(conn), addr, ARRAY_SIZE(addr));

    printk("Received data from %s: %.*s", addr, len, data);
    if (!strcmp(data, "heartbeats")) {
        k_sem_give(&poll_buffer); // Wake up accelerometer thread and poll buffer
    }
}

/* Nordic UART Service callback */
static struct bt_nus_cb nus_cb = {
    .received = bt_receive_cb,
};


// static void set_tx_power(void)
// {
//     struct net_buf *buf, *rsp;
//     int err;
//     uint8_t handle_type = 0x01;  // 0x00 = Advertising handle, 0x01 = Connection handle
//     uint16_t handle = 0x0000;    // Use handle 0 for default advertising set
//     int8_t tx_power = 0;         // TX power in dBm (0 dBm in this case)

//     /* Allocate command buffer */
//     buf = bt_hci_cmd_create(BT_HCI_OP_LE_WRITE_RF_TX_POWER, sizeof(handle_type) + sizeof(handle) + sizeof(tx_power));
//     if (!buf) {
//         LOG_ERR("Failed to allocate HCI buffer");
//         return;
//     }

//     /* Add parameters to the buffer */
//     net_buf_add_u8(buf, handle_type);
//     net_buf_add_le16(buf, handle);
//     net_buf_add_u8(buf, tx_power);

//     /* Send HCI command */
//     err = bt_hci_cmd_send_sync(BT_HCI_OP_LE_WRITE_RF_TX_POWER, buf, &rsp);
//     if (err) {
//         LOG_ERR("Failed to set TX power (err %d)", err);
//     } else {
//         LOG_INF("TX power set to %d dBm", tx_power);
//     }

//     if (rsp) {
//         net_buf_unref(rsp);
//     }
// }


/* BLE Interface functions */

/* BLE initialization function (exposed in ble.h) */
void ble_init(void)
{
    int err;

    dk_leds_init();

    err = bt_enable(NULL);
    if (err) {
        error();
    }

    printk("Bluetooth initialized\n");

    /* Set TX Power to 0 dBm */
    // set_tx_power();

    k_sem_give(&ble_init_ok);

    if (IS_ENABLED(CONFIG_SETTINGS)) {
        settings_load();
    }

    err = bt_nus_init(&nus_cb);
    if (err) {
        printk("Failed to initialize UART service (err: %d)\n", err);
        return;
    }

    err = bt_le_adv_start(BT_LE_ADV_CONN, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));
    if (err) {
        printk("Advertising failed to start (err %d)\n", err);
        return;
    }
}

/* Error handling function (exposed in ble.h) */
void error(void)
{
    dk_set_leds_state(DK_ALL_LEDS_MSK, DK_NO_LEDS_MSK);
    while (true) {
        k_sleep(K_MSEC(1000));
    }
}

void ble_send(uint8_t *buf, uint32_t buf_len) {
    if (current_conn) {
        uint32_t offset = 0;
        while (offset < buf_len) {
            uint32_t chunk_len = (buf_len - offset > BLE_CHUNK_SIZE) ? BLE_CHUNK_SIZE : (buf_len - offset);
            int err = bt_nus_send(current_conn, (void*)(buf + offset), chunk_len);
            if (err) {
                printk("Failed to send data over BLE (err %d)\n", err);
            }
            else {
                printk("Sent FIFO Buffer.\n");
            }
            offset += chunk_len;
        }
    }
}

/* Thread for sending BLE messages */
void ble_send_thread(void *p1, void *p2)
{
    /* Wait until BLE is initialized */
    k_sem_take(&ble_init_ok, K_FOREVER);

    while (1) {
        if (current_conn) {  // Send only if a device is connected
            printk("Retrieving FIFO data\n");
            if (k_fifo_is_empty(&fifo)) {
                printk("FIFO empty.\n");
            }
            uint8_t* fifo_data = k_fifo_get(&fifo, K_MSEC(100));
            if (fifo_data == NULL) {
                printk("FIFO retrieval timed out\n");
                exit(1);
            }
            int err = bt_nus_send(current_conn, fifo_data, 20);
            if (err) {
                printk("Failed to send data over BLE (err %d)", err);
            } else {
                printk("Sent FIFO Buffer.\n");
            }
            k_free(fifo_data);
        }
        k_msleep(100); // Send every 5 seconds
    }
}

//K_THREAD_DEFINE(ble_send_thread_id, BLE_STACKSIZE, ble_send_thread, NULL, NULL, NULL, PRIORITY, 0, 0);
