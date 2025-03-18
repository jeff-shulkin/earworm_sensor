#include "../../include/pfc.h"
#include <limits.h>
/* 1000 msec = 1 sec */
#define SLEEP_TIME_MS   1000

/* The devicetree node identifier for the "led0" alias. */
#define LED0_NODE DT_ALIAS(led0)

/*
 * A build error on this line means your board is unsupported.
 * See the sample documentation for information on how to fix this.
 */
static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(LED0_NODE, gpios);

void power_fail_handler(void)
{
    // Check if the POFWARN event occurred
    if (nrf_power_event_check(NRF_POWER, NRF_POWER_EVENT_POFWARN))
    {
        // Clear the event
        nrf_power_event_clear(NRF_POWER, NRF_POWER_EVENT_POFWARN);

        gpio_pin_toggle_dt(&led);

        printk("Power failure warning detected!\n");
    }
}

/*
 * Configures the accelerometer and nRF chip to go into deep sleep
 *
 */
void pof_deep_sleep(void)
{
    //int ret = pm_device_action_run(cons, PM_DEVICE_ACTION_SUSPEND);
}

void pof_idle_sleep(void)
{
    //pm_state_force(0, &(struct pm_state_info){PM_STATE_SUSPEND_TO_RAM, 0, 0});
}

void configure_pof_interrupt(void)
{
    // Step 1: Initialize the Power-Fail Comparator (PFC)
    nrfx_power_pofwarn_config_t pof_config = {
        .thr = NRF_POWER_POFTHR_V17,  // Set threshold to 1.7V
	    .handler = power_fail_handler
    };

    nrfx_power_pof_init(&pof_config);
    nrfx_power_pof_enable(&pof_config);

    // Step 2: Enable the POFWARN interrupt
    nrf_power_int_enable(NRF_POWER, NRF_POWER_INT_POFWARN_MASK);

    printk("POFWARN interrupt enabled!\n");
}
