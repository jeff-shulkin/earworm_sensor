#include "accel.h"

#include <zephyr/kernel.h>

#include "arm_math.h"

#define BLOCK_SIZE 32  // Number of samples per processing block
#define NUM_TAPS 64    // Filter order

float32_t firStateF32[BLOCK_SIZE + NUM_TAPS - 1];
float32_t inputSignal[BLOCK_SIZE];  // Replace with your IMU data
float32_t outputSignal[BLOCK_SIZE];

// Replace with actual band-pass filter coefficients (generated manually or with tools)
const float32_t firCoeffs32[NUM_TAPS] = {
    /* Your filter coefficients here */
    -0.000088,     -0.000541,     -0.001218,     -0.001998,     -0.002665,     -0.002941,     -0.002606,     -0.001679, 
    -0.000552,     0.000044,     -0.000716,     -0.003331,     -0.007571,     -0.012313,     -0.015789,     -0.016249, 
    -0.012836,     -0.006293,     0.000890,     0.005108,     0.002974,     -0.007077,     -0.023543,     -0.041579, 
    -0.054003,     -0.053428,     -0.034876,     0.002022,     0.052123,     0.105627,     0.150571,     0.176209, 
    0.176209,     0.150571,     0.105627,     0.052123,     0.002022,     -0.034876,     -0.053428,     -0.054003, 
    -0.041579,     -0.023543,     -0.007077,     0.002974,     0.005108,     0.000890,     -0.006293,     -0.012836, 
    -0.016249,     -0.015789,     -0.012313,     -0.007571,     -0.003331,     -0.000716,     0.000044,     -0.000552, 
    -0.001679,     -0.002606,     -0.002941,     -0.002665,     -0.001998,     -0.001218,     -0.000541,     -0.000088
};

arm_fir_instance_f32 filter;  // FIR filter instance

void init_bandpass_filter() {
    arm_fir_init_f32(&filter, NUM_TAPS, firCoeffs32, firStateF32, BLOCK_SIZE);
}

void process_bandpass_filter(float32_t *input, float32_t *output) {
    arm_fir_f32(&filter, input, output, BLOCK_SIZE);
}
