# board_power — MicroPython user C module (CMake / rp2 port)
#
# Build (from micropython/ports/rp2):
#   make BOARD=RPI_PICO2 USER_C_MODULES=../../../my_c_modules/micropython.cmake

add_library(usermod_board_power INTERFACE)

target_sources(usermod_board_power INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/board_power.c
)

target_include_directories(usermod_board_power INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

# hardware_powman is linked by the rp2 port for PICO_RP2350; declare it here
# so the usermod build order / includes stay correct if pulled in early.
if (TARGET hardware_powman)
    target_link_libraries(usermod_board_power INTERFACE hardware_powman)
endif()

target_link_libraries(usermod INTERFACE usermod_board_power)
