#ifndef PFC_H
#define PFC_H

#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/pm/pm.h>
#include <nrfx_power.h>
#include <stdio.h>

#define SAMPLE_TIMEOUT    K_SECONDS(1)

void pof_deep_sleep(void);
void configure_pof_interrupt(void);
void power_fail_handler(void);

#endif /* PFC_H */