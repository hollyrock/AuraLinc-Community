"""
AuraLinc EcoCONNECT
HAL — sensor-pico.net rev 0.5.0 (A660 UART + J2 I2C header).

Power mux is hardware only: Q1 gate is VBUS (not a GPIO). J2 is 3.3 V I2C.
Do not drive connector GPIOs (J1, J4–J6, J8).

                                        Copyright (c) 2026 hollyRock
                                        SPDX-License-Identifier: MIT
"""

import os
import time
import machine
from machine import ADC, I2C, Pin, UART, mem32

# RP2350 PADS_BANK0 (Pico SDK): GPIO pad drive in bits [5:4]; 0b00 = 2 mA
_PADS_BANK0_BASE = 0x40038000
_PADS_GPIO0_REG = _PADS_BANK0_BASE + 0x004
_PADS_DRIVE_MASK = 0x60
_PADS_PULL_MASK = 0x0C  # PUE (bit 2) + PDE (bit 3)

# VSYS sense: GP29 (ADC3). Use pin id 29 so MicroPython calls adc_gpio_init().
VSYS_ADC_GPIO = 29
VSYS_ADC_REF_V = 3.3
VSYS_HW_DIVIDER = 3
VSYS_SAMPLE_COUNT = 10
VSYS_WL_CS_GPIO = 25

# No external VBAT divider. GP26 is J1 Pin_2 only (not sense).
# Battery ≈ VSYS via Q1 when USB is absent; sense with onboard GP29 ADC3 (/3).

# Every user GPIO is on a connector or a firmware peripheral. Do not pulldown them.
UNUSED_GPIO = ()

_vsys_gp25_required = None


def _vsys_gp25_required():
    """True on Pico W / Pico 2 W (GP25 gates VSYS divider). Plain Pico 2: GP25 is the LED."""
    global _vsys_gp25_required
    if _vsys_gp25_required is not None:
        return _vsys_gp25_required
    try:
        machine_name = os.uname().machine.upper()
    except AttributeError:
        machine_name = ""
    _vsys_gp25_required = machine_name.endswith(" W") or " PICO W" in machine_name
    return _vsys_gp25_required


def _gpio_set_drive_2ma(gpio_id):
    reg = _PADS_GPIO0_REG + (gpio_id * 4)
    mem32[reg] = mem32[reg] & ~_PADS_DRIVE_MASK


def _gpio_clear_pulls(gpio_id):
    reg = _PADS_GPIO0_REG + (gpio_id * 4)
    mem32[reg] = mem32[reg] & ~_PADS_PULL_MASK


def gpio_pulldown(pin_ids):
    for pin_id in pin_ids:
        Pin(pin_id, Pin.IN, Pin.PULL_DOWN)


def configure_unused_gpios(active_pins):
    active = set(active_pins)
    for pin_id in UNUSED_GPIO:
        if pin_id not in active:
            Pin(pin_id, Pin.IN, Pin.PULL_DOWN)


def _vsys_wifi_pause():
    try:
        import network

        wlan = network.WLAN(network.STA_IF)
        was_active = wlan.active()
        if was_active:
            wlan.active(False)
            time.sleep_ms(50)
        return was_active
    except Exception:
        return False


def _vsys_wifi_resume(was_active):
    if not was_active:
        return
    try:
        import network

        network.WLAN(network.STA_IF).active(True)
        time.sleep_ms(20)
    except Exception:
        pass


def _enable_vsys_adc_path():
    _gpio_clear_pulls(VSYS_ADC_GPIO)
    if not _vsys_gp25_required():
        return False
    Pin(VSYS_WL_CS_GPIO, Pin.OUT, value=1)
    time.sleep_ms(10)
    return True


def _release_vsys_adc_path(gp25_was_enabled):
    if gp25_was_enabled:
        Pin(VSYS_WL_CS_GPIO, Pin.OUT, value=0)
        time.sleep_ms(5)


def read_vsys_adc_raw(sample_count=VSYS_SAMPLE_COUNT):
    wifi_was_active = _vsys_wifi_pause()
    gp25_enabled = False
    try:
        gp25_enabled = _enable_vsys_adc_path()
        adc = ADC(VSYS_ADC_GPIO)
        total = 0
        for _ in range(sample_count):
            total += adc.read_u16()
        return int(total / sample_count)
    finally:
        _release_vsys_adc_path(gp25_enabled)
        _vsys_wifi_resume(wifi_was_active)


def read_vsys_mv(sample_count=VSYS_SAMPLE_COUNT):
    try:
        raw = read_vsys_adc_raw(sample_count)
        vsys_v = (raw / 65535) * VSYS_ADC_REF_V * VSYS_HW_DIVIDER
        return max(0, min(int(round(vsys_v * 1000)), 65534))
    except OSError:
        return -1


def read_batt_mv(sample_count=VSYS_SAMPLE_COUNT):
    """Battery mV via Pico VSYS (GP29 ADC3 ×3). VBAT feeds VSYS through Q1 when VBUS is low."""
    return read_vsys_mv(sample_count)


def _usb_disable():
    try:
        usb = machine.USBDevice()
        if hasattr(usb, "active"):
            usb.active(False)
            return
    except Exception:
        pass
    try:
        machine.USBDevice().init(active=False)
    except Exception:
        pass


def _usb_enable():
    try:
        usb = machine.USBDevice()
        if hasattr(usb, "active"):
            usb.active(True)
    except Exception:
        pass


def go_deepsleep_ms(ms, disable_usb=True):
    """
    Enter lowest-power sleep until wake (does not return).

    Prefer custom firmware module ``board_power.dormant_ms`` (RP2350 POWMAN
    switched-core power-down). Stock MicroPython ``machine.deepsleep`` on rp2
    is lightsleep + reset and still draws ~mA.

    Wake = full reboot → main.py restarts from the top.
    """
    if ms <= 0:
        ms = 1
    if disable_usb:
        _usb_disable()
    time.sleep_ms(1)
    try:
        import board_power

        board_power.dormant_ms(ms)
    except ImportError:
        pass
    if hasattr(machine, "deepsleep"):
        machine.deepsleep(ms)
    if hasattr(machine, "lightsleep"):
        machine.lightsleep(ms)
    else:
        time.sleep_ms(ms)
    machine.reset()


def _init_i2c0(sda_pin_id, scl_pin_id, freq):
    return I2C(0, sda=Pin(sda_pin_id), scl=Pin(scl_pin_id), freq=freq)


def _init_lora_uart(uart_id, tx_pin_id, rx_pin_id, baud):
    try:
        UART(uart_id).deinit()
    except OSError:
        pass
    _gpio_set_drive_2ma(tx_pin_id)
    return UART(
        uart_id,
        baud,
        tx=Pin(tx_pin_id, Pin.OUT, Pin.PULL_UP),
        rx=Pin(rx_pin_id, Pin.IN, Pin.PULL_UP),
    )


class Board:
    """
    sensor-pico rev 0.5.0: BME280 + BH1750 on J2, A660-900T22 LoRaWAN.

    Sensor2: BME280 + BH1750 on I2C0 GP20/GP21 (J2 Pin_3 / Pin_1). J2 Pin_5 is 3.3 V.
    Sensor3: A660 UART GP0/GP1 (47 Ω), AUX GP3.
    Battery: VSYS (GP29 ADC3 ×3). Q1 is a VBUS-gated P-MOSFET, not a GPIO.
    Connector GPIOs (J1, J4–J6, J8) are left high-Z.
    """

    SENSOR2_I2C_BUS = 0
    SENSOR2_SDA_PIN_ID = 20
    SENSOR2_SCL_PIN_ID = 21
    SENSOR2_I2C_FREQ = 400_000

    SENSOR3_LORA_UART_ID = 0
    SENSOR3_LORA_TX_PIN_ID = 0
    SENSOR3_LORA_RX_PIN_ID = 1
    SENSOR3_LORA_AUX_PIN_ID = 3
    SENSOR3_LORA_BAUD = 9600

    def active_gpio_pins(self):
        pins = {
            self.SENSOR3_LORA_TX_PIN_ID,
            self.SENSOR3_LORA_RX_PIN_ID,
            self.SENSOR3_LORA_AUX_PIN_ID,
            self.SENSOR2_SDA_PIN_ID,
            self.SENSOR2_SCL_PIN_ID,
        }
        if not _vsys_gp25_required():
            pins.add(25)
        return pins

    def __init__(self):
        configure_unused_gpios(self.active_gpio_pins())
        self.sensor2_i2c = _init_i2c0(
            self.SENSOR2_SDA_PIN_ID,
            self.SENSOR2_SCL_PIN_ID,
            self.SENSOR2_I2C_FREQ,
        )
        self.sensor3_lora_uart = _init_lora_uart(
            self.SENSOR3_LORA_UART_ID,
            self.SENSOR3_LORA_TX_PIN_ID,
            self.SENSOR3_LORA_RX_PIN_ID,
            self.SENSOR3_LORA_BAUD,
        )
        self.sensor3_lora_aux = Pin(self.SENSOR3_LORA_AUX_PIN_ID, Pin.IN, Pin.PULL_DOWN)

    def reinit_lora_uart(self):
        self.sensor3_lora_uart = _init_lora_uart(
            self.SENSOR3_LORA_UART_ID,
            self.SENSOR3_LORA_TX_PIN_ID,
            self.SENSOR3_LORA_RX_PIN_ID,
            self.SENSOR3_LORA_BAUD,
        )

    def reinit_i2c(self):
        self.sensor2_i2c = _init_i2c0(
            self.SENSOR2_SDA_PIN_ID,
            self.SENSOR2_SCL_PIN_ID,
            self.SENSOR2_I2C_FREQ,
        )

    def prepare_peripherals_for_sleep(self, uart):
        try:
            uart.deinit()
        except Exception:
            pass
        gpio_pulldown((self.SENSOR3_LORA_TX_PIN_ID, self.SENSOR3_LORA_RX_PIN_ID))
        try:
            self.sensor2_i2c.deinit()
        except Exception:
            pass
        gpio_pulldown((self.SENSOR2_SDA_PIN_ID, self.SENSOR2_SCL_PIN_ID))
        Pin(self.SENSOR3_LORA_AUX_PIN_ID, Pin.IN, Pin.PULL_DOWN)

    def go_deepsleep(self, ms, uart=None, disable_usb=True):
        """Deinit UART/I2C, pulldown those pins only, then POWMAN/stock deepsleep."""
        if uart is not None:
            self.prepare_peripherals_for_sleep(uart)
        go_deepsleep_ms(ms, disable_usb=disable_usb)
