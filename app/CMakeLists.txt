#-------------------------------------------------------------------------------
# Zephyr Example Application
#
# Copyright (c) 2021 Nordic Semiconductor ASA
# SPDX-License-Identifier: Apache-2.0

# Minimum required version of CMake
cmake_minimum_required(VERSION 3.13.1)

# Find the Zephyr package
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})

# Project name for the app
project(app LANGUAGES C)

# Include directories
target_include_directories(app PRIVATE include)

# Source files for the app
target_sources(app PRIVATE src/main.c)
target_sources(app PRIVATE src/power_failure/pfc.c)
target_sources(app PRIVATE src/accel/accel.c)
target_sources(app PRIVATE src/accel/filter.c)
target_sources(app PRIVATE src/ble/ble.c)

# Set the target board
set(BOARD nrf54l15dk_nrf54l15)
