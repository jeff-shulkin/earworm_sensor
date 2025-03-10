#include <zephyr/drivers/sensor/adi/adxl367.h>

#define ADXL367_NODE DT_NODELABEL(adxl367)

const struct device *adxl367_dev;

void check_adxl367(void);
bool setup_adxl367(void);
void retrieve_adxl367_fifo_biffer(void);
