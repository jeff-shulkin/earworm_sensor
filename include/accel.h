#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/rtio/rtio.h>
#include <stdio.h>

#define ADXL367_NODE DT_NODELABEL(adxl367)

// ADXL367 RTIO-relevant definitions
#define N     (1)
#define SQ_SZ (N) // Number of start events queued at a time
#define CQ_SZ (N) // Number of completion events consumed at a time
#define ADXL367_RTIO_BUF_SIZE 512
#define SAMPLE_PERIOD 1
//#define MEM_BLK_COUNT 128
//#define MEM_BLK_SIZE  16
//#define MEM_BLK_ALIGN 4

//RTIO_DEFINE_WITH_MEMPOOL(adxl367_io, SQ_SZ, CQ_SZ, MEM_BLK_COUNT, MEM_BLK_SIZE, MEM_BLK_ALIGN);
//RTIO_SENSOR_IODEV(adxl367_ctx, DEVICE_DT_GET(DT_NODELABEL(adxl367)));


bool check_adxl367(const struct device *dev);
bool setup_adxl367(const struct device *dev, uint16_t *buf);
bool setup_adxl367_fifo(const struct device *dev, uint16_t *buf);
void test_adxl367(const struct device *dev);
void retrieve_adxl367_fifo_biffer(uint16_t* buf, uint8_t buf_size);
void adxl367_trigger_handler(const struct device *dev, const struct sensor_trigger *trigger);

// filter
void init_bandpass_filter();

void process_bandpass_filter(float32_t *input, float32_t *output);