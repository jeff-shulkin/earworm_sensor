#ifndef ACCEL_H
#define ACCEL_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/rtio/rtio.h>
#include <stdio.h>

#include "../../zephyr/drivers/sensor/adi/adxl367/adxl367.h"

#define ADXL367_NODE DT_NODELABEL(adxl367)

// ADXL367 RTIO-relevant definitions
#define N     (1)
#define SQ_SZ (N) // Number of start events queued at a time
#define CQ_SZ (N) // Number of completion events consumed at a time
#define NUM_BLKS 10
#define BLK_SZ 256
#define BLK_ALIGN sizeof(void *) // uint16_t aligned

#define ADXL367_RTIO_BUF_SIZE 1024
#define SAMPLE_PERIOD 1


bool check_adxl367(const struct device *dev);
bool setup_adxl367_fifo_buffer(const struct device *dev);
bool retrieve_adxl367_fifo_buffer(const struct device *dev, uint8_t *buf, uint32_t buf_len);
void retrieve_adxl367_samples(const struct device *dev, int16_t *buf, uint32_t buf_len);
void adxl367_data_ready_handler(const struct device *dev, const struct sensor_trigger *trigger);

void test_adxl367(const struct device *dev);
bool test_adxl367_sensor_stream(const struct device *adxl367_dev);
// filter
void init_bandpass_filter();

void process_bandpass_filter(float32_t *input, float32_t *output);
#endif /* ACCEL_H */