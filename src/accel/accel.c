#include "../../include/accel.h"
#include <stdbool.h>



bool check_adxl367(void)
{
    // First check if the device is ready
    if (!device_is_ready(adxl367_dev)) {
        printk("ADXL367 is not ready\n");
        return false;
    }
    return true;
}

bool setup_adxl367(void)
{
    // Read ODR from device tree
    struct sensor_value odr;
    odr.val1 = DT_PROP(ADXL367_NODE, odr);
    odr.val2 = 0;

    struct sensor_trigger fifo_int;
    fifo_int.type = SENSOR_TRIG_DATA_READY;
    fifo_int.chan = SENSOR_CHAN_ACCEL_XYZ;

    enum adxl367_fifo_mode fifo_mode = ADXL367_TRIGGERED_MODE;
    enum adxl367_fifo_format fifo_format = ADXL367_FIFO_FORMAT_XYZ;
    enum adxl367_fifo_read_mode fifo_read_mode = ADXL367_14B_CHID;
    uint16_t fifo_sets_nb = 97; // floor((512 * 8) / (3 * 14))

    // Set sampling rate to 50 Hz
    if (sensor_attr_set(adxl367_dev, SENSOR_CHAN_ALL, SENSOR_ATTR_SAMPLING_FREQUENCY, &odr)) {
        printk("ADXL367 ODR set failed.\n");
        return false;
    }
    printk("ADXL367 ODR successfully set.\n");
    
    // Setup FIFO buffer
    if (adxl367_fifo_setup(adxl367_dev, adxl367_fifo_mode, adxl367_fifo_format, 
        adxl367_fifo_read_mode, fifo_sets_nb)) {
        printk("ADXL367 FIFO setup failed.\n");
        return false;
    } 
    printk("ADXL367 FIFO successfully set.\n");

    // Enable interrupt
    if (sensor_trigger_set(adxl367_dev, &fifo_int)) {
        printk("ADXL367 FIFO interrupt setup failed.\n");
        return false;
    }
    printk("ADXL367 FIFO interrupt successfully set.\n");
    
    return true;
}

void retrieve_adxl367_fifo_buffer(void) {
 // TODO
}
