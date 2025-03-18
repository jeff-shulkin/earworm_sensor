#include "../../include/accel.h"
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/rtio/rtio.h>
#include <stdbool.h>

//RTIO_DEFINE(adxl367_ctx_user, SQ_SZ, CQ_SZ);



bool check_adxl367(const struct device *adxl367_dev)
{
    adxl367_dev = DEVICE_DT_GET_ONE(adi_adxl367);
    if (!adxl367_dev) {
        printk("Failed to get ADXL367 device from DT\n");
    }
    printf("Sensor state result: %d\n", adxl367_dev->state->init_res);
    printk("Sensor initialized: %d\n", (uint8_t)adxl367_dev->state->initialized);
    // First check if the device is ready
    if (!device_is_ready(adxl367_dev)) {
        printk("ADXL367 is not ready\n");
        return false;
    }
    return true;
}

bool setup_adxl367(const struct device *adxl367_dev, uint16_t *buf)
{
    // Read ODR from device tree
    struct sensor_value odr;
    odr.val1 = DT_PROP(ADXL367_NODE, odr);
    odr.val2 = 0;

    struct sensor_trigger fifo_int;
    fifo_int.type = SENSOR_TRIG_DATA_READY;
    fifo_int.chan = SENSOR_CHAN_ACCEL_XYZ;

    // Set sampling rate to 50 Hz
    if (sensor_attr_set(adxl367_dev, SENSOR_CHAN_ALL, SENSOR_ATTR_SAMPLING_FREQUENCY, &odr)) {
        printk("ADXL367 ODR set failed.\n");
        return false;
    }
    printk("ADXL367 ODR successfully set.\n");

    // Enable interrupt
    if (sensor_trigger_set(adxl367_dev, &fifo_int, adxl367_trigger_handler)) {
        printk("ADXL367 FIFO interrupt setup failed.\n");
        return false;
    }
    printk("ADXL367 FIFO interrupt successfully set.\n");

    // Setup ADXL367 FIFO 
    setup_adxl367_fifo(adxl367_dev, buf);
    
    return true;
}

bool setup_adxl367_fifo(const struct device *dev, uint16_t *buf) {
    // Set up RTIO with EasyDMA
    //struct device *dma = DEVICE_DT_GET(DT_NODE(dma0));
    //const struct rtio_executor *rtio_dma_exec = dma_rtio_executor(dma);
    //rtio_set_executor(adxl367_ctx, rtio_dma_exec);

    //struct rtio_iodev *adxl367_iodev = (struct )(struct adxl367_data *)(dev->data);
    //struct rtio_sqe *sqe = rtio_sqe_acquire(&adxl367_ctx);
    //rtio_sqe_prep_read(sqe, d, RTIO_PRIO_HIGH, (uint8_t*)buf, ADXL367_RTIO_BUF_SIZE, NULL);
    return true;
}

void retrieve_adxl367_fifo_buffer(const struct device *dev, uint16_t *buf) {

    // if (rtio_submit(&adxl367_ctx_user, 1)) {
    //     printk("RTIO submit failed. Exiting\n");
    //     exit(1);
    // }
    // k_msleep(SAMPLE_PERIOD);
    // struct rtio_cqe *cqe = rtio_cqe_consume(&adxl367_ctx_user);

    // if (cqe == NULL) {
    //     printk("No completion events available");
    //     exit(1);
    // }

    // if(cqe->result < 0) {
    //     printk("read failed!");
    //     exit(1); // For now just exit if we fail to read
    // }

    // // Bytes read into the buffer
    // int32_t bytes_read = cqe->result;
    // *buf = cqe->userdata;

    // /* Release completion queue event */
    // rtio_cqe_release(&adxl367_ctx_user, cqe);

}

void adxl367_trigger_handler(const struct device *dev, const struct sensor_trigger *trigger) {
    printf("TRIGGER HANDLER: NOTHING EVER HAPPENS\n");
}

void test_adxl367(const struct device *adxl367_dev) {
    struct sensor_value accel_vals[3]; 
    while(1) {
        /* 20ms period, 100Hz Sampling frequency */
		k_sleep(K_MSEC(20));
        sensor_sample_fetch(adxl367_dev);
        sensor_channel_get(adxl367_dev, SENSOR_CHAN_ACCEL_XYZ, accel_vals);
        printf("AX: %d.%06d; AY: %d.%06d; AZ: %d.%06d; \n",
            accel_vals[0].val1, accel_vals[0].val2,
            accel_vals[1].val1, accel_vals[1].val2,
            accel_vals[2].val1, accel_vals[2].val2);
    }
}


