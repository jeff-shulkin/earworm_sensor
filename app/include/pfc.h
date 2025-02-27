#include <nrfx_power.h>
#include <zephyr/kernel.h>
#include <stdio.h>
#include <zephyr/drivers/gpio.h>


void pof_deep_sleep(void);
void configure_pof_interrupt(void);
void power_fail_handler(void);
