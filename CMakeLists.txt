cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})

project(earworm_sensor)

target_sources(app PRIVATE src/main.c)
target_sources(app PRIVATE src/power_failure/pfc.c)
target_sources(app PRIVATE src/accel/accel.c)
# target_sources(app PRIVATE src/accel/filter.c)
# target_sources(app PRIVATE src/ble/ble.c)

#set(BOARD nrf54l15dk_nrf54l15)