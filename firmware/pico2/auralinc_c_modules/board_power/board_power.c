/*
 * board_power — RP2350 POWMAN low-power sleep for MicroPython (user C module)
 *
 * Exposes: board_power.dormant_ms(ms)
 *
 * Uses Pico SDK hardware_powman to power down the switched core (and SRAM /
 * XIP cache) and wake from the always-on timer. Wake triggers a full chip
 * reboot → MicroPython restarts → main.py runs from the top (same contract
 * as machine.deepsleep on rp2, but far lower idle current than lightsleep).
 *
 * Requires: MicroPython built for RPI_PICO2 / RP2350 with this usermod linked.
 *
 *                                        Copyright (c) 2026 hollyRock
 *                                        SPDX-License-Identifier: MIT
 *
 */

#include "py/runtime.h"
#include "py/mperrno.h"

#if PICO_RP2350

#include "hardware/powman.h"
#include "pico.h"

static void board_power_powman_sleep_ms(uint32_t duration_ms) {
    if (duration_ms < 1u) {
        duration_ms = 1u;
    }

    /* AON timer must run from LPOSC so it survives core power-down. */
    powman_timer_set_1khz_tick_source_lposc();
    if (!powman_timer_is_running()) {
        powman_timer_start();
    }

    powman_disable_all_wakeups();
    powman_disable_alarm_wakeup();
    powman_clear_alarm();

    /*
     * Sleep: all switched domains off (P1.7-style).
     * Wake: restore switched core + XIP + both SRAM banks (normal boot path).
     * Bit set == domain ON (see hardware/powman.h helpers).
     */
    powman_power_state sleep_state = POWMAN_POWER_STATE_NONE;
    powman_power_state wakeup_state = POWMAN_POWER_STATE_NONE;
    wakeup_state = powman_power_state_with_domain_on(wakeup_state, POWMAN_POWER_DOMAIN_SWITCHED_CORE);
    wakeup_state = powman_power_state_with_domain_on(wakeup_state, POWMAN_POWER_DOMAIN_XIP_CACHE);
    wakeup_state = powman_power_state_with_domain_on(wakeup_state, POWMAN_POWER_DOMAIN_SRAM_BANK0);
    wakeup_state = powman_power_state_with_domain_on(wakeup_state, POWMAN_POWER_DOMAIN_SRAM_BANK1);

    if (!powman_configure_wakeup_state(sleep_state, wakeup_state)) {
        mp_raise_OSError(MP_EINVAL);
    }

    /* Force cold boot into flash image on wake (not POWMAN resume vector). */
    powman_hw->boot[0] = 0;
    powman_hw->boot[1] = 0;
    powman_hw->boot[2] = 0;
    powman_hw->boot[3] = 0;

    uint64_t wake_at_ms = powman_timer_get_ms() + (uint64_t)duration_ms;
    powman_enable_alarm_wakeup_at_ms(wake_at_ms);

    int rc = powman_set_power_state(sleep_state);
    if (rc != PICO_OK) {
        mp_raise_OSError(MP_EIO);
    }

    /* Switched-core power-down completes on WFI. */
    while (true) {
        __wfi();
    }
}

#else /* !PICO_RP2350 */

static void board_power_powman_sleep_ms(uint32_t duration_ms) {
    (void)duration_ms;
    mp_raise_NotImplementedError(MP_ERROR_TEXT("board_power.dormant_ms requires RP2350"));
}

#endif

static mp_obj_t board_power_dormant_ms(mp_obj_t ms_in) {
    mp_int_t ms = mp_obj_get_int(ms_in);
    if (ms < 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("ms must be >= 0"));
    }
    board_power_powman_sleep_ms((uint32_t)ms);
    /* Unreachable if POWMAN sleep succeeded (chip reboots on wake). */
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(board_power_dormant_ms_obj, board_power_dormant_ms);

static const mp_rom_map_elem_t board_power_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_board_power) },
    { MP_ROM_QSTR(MP_QSTR_dormant_ms), MP_ROM_PTR(&board_power_dormant_ms_obj) },
};
static MP_DEFINE_CONST_DICT(board_power_module_globals, board_power_module_globals_table);

const mp_obj_module_t board_power_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&board_power_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_board_power, board_power_user_cmodule);
