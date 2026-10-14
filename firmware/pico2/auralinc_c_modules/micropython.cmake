# Top-level USER_C_MODULES entry for AuraLinc Pico 2 custom firmware.
# Point make at this file:
#   make BOARD=RPI_PICO2 USER_C_MODULES=<abs-path>/auralinc_c_modules/micropython.cmake

include(${CMAKE_CURRENT_LIST_DIR}/board_power/micropython.cmake)
