#include "accel.h"

bool check_adxl367(void)
{
    // First check if the device is ready
    if (!device_is_ready(adxl367_dev)) {
        printk("ADXL367 is not ready\n");
        return false;
    }
    return true;
}

