#include "../../include/accel.h"
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/sys/util_macro.h>
#include <zephyr/kernel.h>
#include <zephyr/rtio/rtio.h>
#include <zephyr/drivers/sensor.h>

#define NUM_SENSORS 1
SENSOR_DT_STREAM_IODEV(accel_stream, DT_NODELABEL(adxl367), \
    {SENSOR_TRIG_FIFO_FULL, SENSOR_STREAM_DATA_INCLUDE});

RTIO_DEFINE_WITH_MEMPOOL(accel_ctx, SQ_SZ, CQ_SZ, NUM_BLKS, BLK_SZ, BLK_ALIGN);


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

    enum adxl367_fifo_mode fifo_mode = ADXL367_OLDEST_SAVED;
    enum adxl367_fifo_format fifo_format = ADXL367_FIFO_FORMAT_XYZ;
    enum adxl367_fifo_read_mode read_mode = ADXL367_14B_CHID;
    uint8_t sets_nb = 171;

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

    ret = adxl367_fifo_setup(dev, ADXL367_FIFO_DISABLED, fifo_format, read_mode, sets_nb);
    if (ret) {
        printk("ADXL367 FIFO Buffer disable failed.\n");
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

    ret = sensor_stream(&accel_stream, &accel_ctx, NULL, &handle);
    if (ret) {
        printk("ADXL FIFO setup: failed to start sensor stream.\n");
        return false;
    }

    return true;
}

bool retrieve_adxl367_fifo_buffer(const struct device *dev, uint8_t *buf, uint32_t buf_len) {
    int rc;
    struct rtio_cqe *cqe;

    cqe = rtio_cqe_consume_block(&accel_ctx);
    if (cqe->result != 0) {
        printk("async read failed %d\n", cqe->result);
        return false;
    }
    
	rc = rtio_cqe_get_mempool_buffer(&accel_ctx, cqe, &buf, &buf_len);
	if (rc != 0) {
		printk("get mempool buffer failed %d\n", rc);
		return false;
	}

    rtio_cqe_release(&accel_ctx, cqe);
    rtio_release_buffer(&accel_ctx, buf, buf_len);
    //rtio_sqe_prep_read_with_pool(sqe, iodev, RTIO_PRIO_HIGH, NULL);
    return true;
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

bool test_adxl367_sensor_stream(const struct device *adxl367_dev) {
	int rc = 0;
	const struct sensor_decoder_api *decoder;
    struct sensor_chan_spec accel_chan = { SENSOR_CHAN_ACCEL_XYZ, 0 };
	struct rtio_cqe *cqe;
	uint8_t *buf;
	uint32_t buf_len;
	struct rtio_sqe *handle;
	uint8_t accel_buf[1024] = { 0 };
	struct sensor_three_axis_data *accel_data = (struct sensor_three_axis_data *)accel_buf;
    
	/* Start the stream */
	printk("sensor_stream\n");
	sensor_stream(&accel_stream, &accel_ctx, NULL, &handle);

	while (1) {
		cqe = rtio_cqe_consume_block(&accel_ctx);

		if (cqe->result != 0) {
			printk("async read failed %d\n", cqe->result);
			return false;
		}

		rc = rtio_cqe_get_mempool_buffer(&accel_ctx, cqe, &buf, &buf_len);

		if (rc != 0) {
			printk("get mempool buffer failed %d\n", rc);
			return false;
		}

		const struct device *sensor = adxl367_dev;

		rtio_cqe_release(&accel_ctx, cqe);

		rc = sensor_get_decoder(sensor, &decoder);

		if (rc != 0) {
			printk("sensor_get_decoder failed %d\n", rc);
			return false;
		}

		/* Frame iterator values when data comes from a FIFO */
		uint32_t accel_fit = 0;

		/* Number of sensor data frames */
		uint16_t xl_count, frame_count;

		rc = decoder->get_frame_count(buf, accel_chan, &xl_count);

		if (rc != 0) {
			printk("sensor_get_frame failed %d\n", rc);
			return false;
		}

		frame_count = xl_count;

		/* If a tap has occurred lets print it out */
		if (decoder->has_trigger(buf, SENSOR_TRIG_TAP)) {
			printk("Tap! Sensor %s\n", adxl367_dev->name);
		}

		/* Decode all available sensor FIFO frames */
		printk("FIFO count - %d\n", frame_count);

		int i = 0;

		while (i < frame_count) {
			int8_t c = 0;

			/* decode and print Accelerometer FIFO frames */
			c = decoder->decode(buf, accel_chan, &accel_fit, 8, accel_data);

			for (int k = 0; k < c; k++) {
				printk("XL data for %s %lluns (%" PRIq(6) ", %" PRIq(6)
				       ", %" PRIq(6) ")\n", adxl367_dev->name,
				       PRIsensor_three_axis_data_arg(*accel_data, k));
			}
			i += c;
		}

		rtio_release_buffer(&accel_ctx, buf, buf_len);
	}
    return true;
    // uint8_t buffer[1024] = {0};
    // struct rtio_sqe *handle;
    // int ret = 0;
    // ret = sensor_stream(&accel_stream, &accel_ctx, buffer, &handle);
    // if (ret) {
    //     printk("Sensor stream return value: %d\n", ret);
    //     return false;
    // }
    // while (1) {}
    // rtio_sqe_cancel(handle);
    // for (size_t i = 0; i < 1024; i++) {
    //     printf("0x%02X ", buffer[i]);  // Print each byte in hexadecimal
    //     if ((i + 1) % 16 == 0) {  // Print new line every 16 bytes
    //         printf("\n");
    //     }
    // }
    // printf("\n");
}
