/*
 * Copyright (c) 2021 Nordic Semiconductor ASA
 * SPDX-License-Identifier: Apache-2.0
 */

#include "../include/pfc.h"
#include "../include/accel.h"
#include "../include/ble.h"

 #include <zephyr/kernel.h>
 #include <zephyr/device.h>
 #include <zephyr/devicetree.h>
 #include <stdio.h>
 #include <zephyr/drivers/gpio.h>

 
 /* 1000 msec = 1 sec */
 #define SLEEP_TIME_MS   1000
 
 /* The devicetree node identifier for the "led0" alias. */
 #define LED0_NODE DT_ALIAS(led0)
 #define ACCEL_NODE DT_ALIAS(adxl367)
 K_FIFO_DEFINE(fifo);
 K_SEM_DEFINE(poll_buffer, 0, 1);

 /*
  * A build error on this line means your board is unsupported.
  * See the sample documentation for information on how to fix this.
  */
 static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(LED0_NODE, gpios);
 const struct device *const adxl367_dev = DEVICE_DT_GET(DT_NODELABEL(adxl367));

int main(void)
{
	uint8_t buffer[ADXL367_RTIO_BUF_SIZE] = {0};
	int16_t sample_buffer[128 * 3] = {0};
    printk("Initializing Power-Fail Comparator...\n");
	int ret;

	if (!gpio_is_ready_dt(&led)) {
		return 0;
	}

	ret = gpio_pin_configure_dt(&led, GPIO_OUTPUT_ACTIVE);
	if (ret < 0) {
		return 0;
	}

    configure_pof_interrupt();

	ble_init();

	if (!check_adxl367(adxl367_dev)) {
		exit(1);
	}

//    if (!setup_adxl367_fifo_buffer(adxl367_dev, buffer)) {
// 	   exit(1);
//    }
	//test_adxl367(adxl367_dev);

	struct sensor_trigger trig = {
		.type = SENSOR_TRIG_DATA_READY,
		.chan = SENSOR_CHAN_ACCEL_XYZ,
	};

	ret = sensor_trigger_set(adxl367_dev, &trig, adxl367_data_ready_handler);
	if (ret < 0) {
		printf("Could not set tap trigger with error code: %d\n", ret);
		return ret;
	}

    while (1)
    {
     	// k_sleep(K_SECONDS(1));  // Sleep to reduce CPU usage
		// if (!retrieve_adxl367_fifo_buffer(adxl367_dev, buffer, 768)) {
		// 	printk("Failed to retrieve FIFO buffer.\n");
		// 	exit(1);
		// }
		retrieve_adxl367_samples(adxl367_dev, sample_buffer, 128);
		ble_send((uint8_t*)sample_buffer, 128 * 3);
    }

	return 0;
}
