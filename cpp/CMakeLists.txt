cmake_minimum_required(VERSION 3.24)

include(pico-sdk/pico_sdk_init.cmake)
project(cpp C CXX)

pico_sdk_init()

# Trivial UF2 that runs directly from RAM and does not get written to the flash
# at all. Simply reboots the RP2040.
add_executable(uf2_exit uf2_exit.cc)
target_link_libraries(uf2_exit pico_runtime hardware_watchdog)
pico_set_binary_type(uf2_exit no_flash)
pico_add_extra_outputs(uf2_exit)
