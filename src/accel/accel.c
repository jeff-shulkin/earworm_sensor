#include "../../include/accel.h"
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/rtio/rtio.h>
#include <zephyr/drivers/sensor.h>
#include <stdbool.h>

SENSOR_DT_STREAM_IODEV(accel_stream, DT_NODELABEL(adxl367),
    {SENSOR_TRIG_FIFO_FULL, SENSOR_STREAM_DATA_INCLUDE},
    {SENSOR_TRIG_FIFO_WATERMARK, SENSOR_STREAM_DATA_NOP});

RTIO_DEFINE(accel_ctx, 1, 1);


bool check_adxl367(const struct device *adxl367_dev)
{
    if (!adxl367_dev) {
        printk("Failed to get ADXL367 device from DT\n");
    }
    printk("Sensor state result: %d\n", adxl367_dev->state->init_res);
    printk("Sensor initialized: %d\n", (uint8_t)adxl367_dev->state->initialized);
    // First check if the device is ready
    if (!device_is_ready(adxl367_dev)) {
        printk("ADXL367 is not ready\n");
        return false;
    }
    return true;
}

bool setup_adxl367_fifo_buffer(const struct device *dev, struct rtio_sqe *handle) {
    int ret;

    enum adxl367_fifo_mode fifo_mode = ADXL367_STREAM_MODE;
    enum adxl367_fifo_format fifo_format = ADXL367_FIFO_FORMAT_XYZ;
    enum adxl367_fifo_read_mode read_mode = ADXL367_14B_CHID;
    uint8_t sets_nb = 128;

    struct sensor_trigger trig = {
		.type = SENSOR_TRIG_FIFO_FULL,
		.chan = SENSOR_CHAN_ACCEL_XYZ,
	};

    // Briefly disable measurement mode so we can alter fifo setup
    ret = adxl367_set_op_mode(dev, ADXL367_STANDBY);
    if (ret) {
        printk("ADXL367 FIFO setup: couldn't set operation mode to standby.\n");
        return false;
    }

    ret = adxl367_fifo_setup(dev, fifo_mode, fifo_format, read_mode, sets_nb);
    if (ret) {
        printk("ADXL367 FIFO Buffer initialization failed.\n");
        return false;
    }

    ret = adxl367_set_op_mode(dev, ADXL367_MEASURE);
    if (ret) {
        printk("ADXL367 FIFO setup: couldn't set operation mode to measurement.\n");
        return false;
    }

    sensor_stream(&accel_stream, &accel_ctx, NULL, handle);

    return true;
}

void retrieve_adxl367_fifo_buffer(const struct device *dev, uint8_t *buf, uint32_t buf_len) {
    int rc;
    struct rtio_cqe *cqe;
    cqe = rtio_cqe_consume_block(&accel_stream);
    if (cqe->result != 0) {
        printk("async read failed %d\n", cqe->result);
        return;
    }
    memcpy(buf, (uint8_t *)cqe->userdata, buf_len);
    rtio_cqe_release(&accel_stream, cqe);
}

void adxl367_trigger_handler(const struct device *dev, const struct sensor_trigger *trigger) {
    printf("TRIGGER HANDLER: NOTHING EVER HAPPENS\n");
}

void test_adxl367(const struct device *adxl367_dev) {
    adxl367_dev = DEVICE_DT_GET_ONE(adi_adxl367);
    struct sensor_value accel_vals[3]; 
    while(1) {
        /* 20ms period, 100Hz Sampling frequency */
		k_sleep(K_MSEC(20));
        sensor_sample_fetch(adxl367_dev);
        sensor_channel_get(adxl367_dev, SENSOR_CHAN_ACCEL_XYZ, accel_vals);
        printk("AX: %d.%06d; AY: %d.%06d; AZ: %d.%06d; \n",
            accel_vals[0].val1, accel_vals[0].val2,
            accel_vals[1].val1, accel_vals[1].val2,
            accel_vals[2].val1, accel_vals[2].val2);
    }
}


