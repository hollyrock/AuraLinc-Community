"""
AuraLinc EcoCONNECT Application — sensor-pico rev 0.5.0
- BME280 + BH1750 on J2 (I2C0 GP20/GP21, 3.3 V always on)
- A660 LoRaWAN (UART GP0/GP1, AUX GP3)
- deepsleep + session persist (no sensor-rail GPIO)

Boot flow (single-shot — deepsleep resets Pico and re-runs main.py):
  wake modem → live session | ABP from session.json | OTAA
  (OTAA keys from device.json) → sensors + uplink → bump fcnt → CLPM
  → deinit UART/I2C + deepsleep

                                        Copyright (c) 2026 hollyRock
                                        SPDX-License-Identifier: MIT
"""

import struct
import time

from machine import Pin

try:
    import ujson as json
except ImportError:
    import json

from hal_hardware import Board, read_batt_mv

# ---------------------------------------------------------------------------
# Production defaults + debug toggles
# ---------------------------------------------------------------------------
SLEEP_TIME_MS = 7_200_000  # 2 hours; deepsleep resets then re-runs main.py
# SLEEP_TIME_MS = 60_000   # debug: 60 s between cycles

DEBUG_USB = False   # True: keep USB on across deepsleep (higher idle current)
DEBUG_LOG = False   # True: UART/print diagnostics
DEBUG_I2C_SCAN = False  # True: print I2C scan at boot

# ---------------------------------------------------------------------------
# Sensors
# ---------------------------------------------------------------------------
BH1750_ADDR = 0x23
BH1750_ONE_SHOT_HIGH = 0x20
BH1750_POWER_DOWN = 0x00

BME280_REG_CTRL_MEAS = 0xF4
BME280_REG_CONFIG = 0xF5
BME280_REG_CTRL_HUM = 0xF2
BME280_MODE_SLEEP = 0x00
BME280_MODE_NORMAL = 0x27
BME280_CONFIG_STANDBY = 0xA0
BME280_ADDR_CANDIDATES = (0x76, 0x77)
BME280_CHIP_ID = 0x60

PAYLOAD_INVALID_U8 = 0xFF
PAYLOAD_INVALID_U16 = 0xFFFF
PAYLOAD_FMT = ">BBHHH"

LED_PULSE_MS = 80
VSYS_SAMPLE_COUNT = 10

# ---------------------------------------------------------------------------
# LoRaWAN / A660
# ---------------------------------------------------------------------------
LORA_DTRX_CONFIRM = 1
LORA_DTRX_NB_TRIALS = 3
LORA_APP_FPORT = 1
LORA_JOIN_CONFIRM_PAYLOAD = b"\x01"
LORA_JOIN_CONFIRM_DELAY_S = 15
LORA_JOIN_CONFIRM_DTRX_CONFIRM = 0

LORA_REGION = 3
LORA_CRXP_PARAMS = "0,2,923200000"
LORA_MAX_TX_POWER = 13

LORA_BOOT_SETTLE_MS = 800
LORA_CMD_TIMEOUT_MS = 5000
LORA_SEND_TIMEOUT_MS = 8000
LORA_DTRX_IDLE_MS = 200
LORA_JOIN_TIMEOUT_MS = 120_000
LORA_JOIN_POLL_MS = 2000
LORA_DJOIN_PARAMS = "1,1,8,5"
LORA_FAIL_RETRY_SLEEP_MS = 60_000

# ---------------------------------------------------------------------------
# Flash files (Pico filesystem)
# ---------------------------------------------------------------------------
# device.json — per-board OTAA secrets (gitignored). Copy from device.json.example.
# session.json — runtime ABP session after join (written on-device).
DEVICE_PATH = "device.json"
SESSION_PATH = "session.json"


def _log(*args, **kwargs):
    if DEBUG_LOG:
        print(*args, **kwargs)


# =============================================================================
# Flash IO — device.json (OTAA secrets)
# =============================================================================

def device_load():
    """
    Load OTAA credentials from device.json.
    Returns dict with deveui/appeui/appkey (normalized hex) or None.
    """
    try:
        with open(DEVICE_PATH, "r") as f:
            data = json.load(f)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return {
            "deveui": _lora_hex_field("deveui", data.get("deveui", ""), 8),
            "appeui": _lora_hex_field("appeui", data.get("appeui", ""), 8),
            "appkey": _lora_hex_field("appkey", data.get("appkey", ""), 16),
        }
    except (ValueError, TypeError, AttributeError):
        return None


# =============================================================================
# Flash IO — session.json
# =============================================================================

def session_clear():
    try:
        import os

        os.remove(SESSION_PATH)
        _log("Session: cleared", SESSION_PATH)
    except OSError:
        pass


def session_load():
    """Return dict with devaddr/nwkskey/appskey/fcnt or None if missing/invalid."""
    try:
        with open(SESSION_PATH, "r") as f:
            data = json.load(f)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    for key in ("devaddr", "nwkskey", "appskey"):
        val = data.get(key)
        if not isinstance(val, str) or not val:
            return None
    try:
        data["devaddr"] = _lora_hex_field("devaddr", data["devaddr"], 4)
        data["appskey"] = _lora_hex_field("appskey", data["appskey"], 16)
        data["nwkskey"] = _lora_hex_field("nwkskey", data["nwkskey"], 16)
    except ValueError:
        return None
    try:
        data["fcnt"] = int(data.get("fcnt", 0))
    except (TypeError, ValueError):
        data["fcnt"] = 0
    if data["fcnt"] < 0:
        data["fcnt"] = 0
    return data


def session_save(devaddr, nwkskey, appskey, fcnt):
    data = {
        "devaddr": str(devaddr).lower(),
        "nwkskey": str(nwkskey).lower(),
        "appskey": str(appskey).lower(),
        "fcnt": int(fcnt),
    }
    try:
        with open(SESSION_PATH, "w") as f:
            json.dump(data, f)
        _log("Session: saved fcnt=%d" % data["fcnt"])
        return True
    except OSError as e:
        _log("Session: save failed", e)
        return False


def session_bump_fcnt(session):
    if session is None:
        return None
    session["fcnt"] = int(session.get("fcnt", 0)) + 1
    session_save(
        session["devaddr"],
        session["nwkskey"],
        session["appskey"],
        session["fcnt"],
    )
    return session


# =============================================================================
# Sensors
# =============================================================================

def _read_bh1750_lux(i2c, addr=BH1750_ADDR):
    i2c.writeto(addr, b"\x01")
    time.sleep_ms(10)
    i2c.writeto(addr, bytes((BH1750_ONE_SHOT_HIGH,)))
    time.sleep_ms(180)
    raw = i2c.readfrom(addr, 2)
    return (raw[0] << 8 | raw[1]) / 1.2


def _bme280_detect_addr(i2c):
    found = set(i2c.scan())
    for addr in BME280_ADDR_CANDIDATES:
        if addr in found:
            return addr
    return None


def _bme280_read_u8(i2c, addr, reg):
    return i2c.readfrom_mem(addr, reg, 1)[0]


def _bme280_write_u8(i2c, addr, reg, val):
    i2c.writeto_mem(addr, reg, bytes((val,)))


def _bme280_load_coeffs(i2c, addr):
    cal1 = i2c.readfrom_mem(addr, 0x88, 24)
    dig_h1 = i2c.readfrom_mem(addr, 0xA1, 1)[0]
    cal2 = i2c.readfrom_mem(addr, 0xE1, 7)
    dig_t1 = cal1[0] | (cal1[1] << 8)
    dig_t2 = struct.unpack("<h", cal1[2:4])[0]
    dig_t3 = struct.unpack("<h", cal1[4:6])[0]
    dig_p1 = cal1[6] | (cal1[7] << 8)
    dig_p2 = struct.unpack("<h", cal1[8:10])[0]
    dig_p3 = struct.unpack("<h", cal1[10:12])[0]
    dig_p4 = struct.unpack("<h", cal1[12:14])[0]
    dig_p5 = struct.unpack("<h", cal1[14:16])[0]
    dig_p6 = struct.unpack("<h", cal1[16:18])[0]
    dig_p7 = struct.unpack("<h", cal1[18:20])[0]
    dig_p8 = struct.unpack("<h", cal1[20:22])[0]
    dig_p9 = struct.unpack("<h", cal1[22:24])[0]
    dig_h2 = cal2[0] | (cal2[1] << 8)
    dig_h3 = struct.unpack("b", cal2[2:3])[0]
    dig_h4 = (cal2[3] << 4) | (cal2[4] & 0x0F)
    if dig_h4 > 32767:
        dig_h4 -= 65536
    dig_h5 = (cal2[5] << 4) | (cal2[4] >> 4)
    if dig_h5 > 32767:
        dig_h5 -= 65536
    dig_h6 = struct.unpack("b", cal2[6:7])[0]
    return {
        "t1": dig_t1,
        "t2": dig_t2,
        "t3": dig_t3,
        "p1": dig_p1,
        "p2": dig_p2,
        "p3": dig_p3,
        "p4": dig_p4,
        "p5": dig_p5,
        "p6": dig_p6,
        "p7": dig_p7,
        "p8": dig_p8,
        "p9": dig_p9,
        "h1": dig_h1,
        "h2": dig_h2,
        "h3": dig_h3,
        "h4": dig_h4,
        "h5": dig_h5,
        "h6": dig_h6,
    }


def _bme280_init(i2c, addr):
    if _bme280_read_u8(i2c, addr, 0xD0) != BME280_CHIP_ID:
        raise OSError("BME280 chip id mismatch")
    _bme280_write_u8(i2c, addr, 0xE0, 0xB6)
    time.sleep_ms(10)
    coeffs = _bme280_load_coeffs(i2c, addr)
    _bme280_write_u8(i2c, addr, BME280_REG_CTRL_HUM, 0x01)
    _bme280_write_u8(i2c, addr, BME280_REG_CTRL_MEAS, BME280_MODE_NORMAL)
    _bme280_write_u8(i2c, addr, BME280_REG_CONFIG, BME280_CONFIG_STANDBY)
    time.sleep_ms(100)
    return coeffs


def _bme280_sleep(i2c, addr):
    _bme280_write_u8(i2c, addr, BME280_REG_CTRL_MEAS, BME280_MODE_SLEEP)


def _power_down_sensors(i2c, bme_addr):
    if bme_addr is not None:
        try:
            _bme280_sleep(i2c, bme_addr)
        except OSError:
            pass
    try:
        i2c.writeto(BH1750_ADDR, bytes((BH1750_POWER_DOWN,)))
    except OSError:
        pass


def _bme280_compensate_temp(coeffs, adc_t):
    var1 = (((adc_t >> 3) - (coeffs["t1"] << 1)) * coeffs["t2"]) >> 11
    var2 = (
        ((((adc_t >> 4) - coeffs["t1"]) * ((adc_t >> 4) - coeffs["t1"])) >> 12)
        * coeffs["t3"]
    ) >> 14
    t_fine = var1 + var2
    temp_c = ((t_fine * 5 + 128) >> 8) / 100.0
    return t_fine, temp_c


def _bme280_compensate_press(coeffs, t_fine, adc_p):
    var1 = t_fine - 128000
    var2 = var1 * var1 * coeffs["p6"]
    var2 = var2 + ((var1 * coeffs["p5"]) << 17)
    var2 = var2 + (coeffs["p4"] << 35)
    var1 = ((var1 * var1 * coeffs["p3"]) >> 8) + ((var1 * coeffs["p2"]) << 12)
    var1 = (((1 << 47) + var1) * coeffs["p1"]) >> 33
    if var1 == 0:
        return 0.0
    p = 1048576 - adc_p
    p = (((p << 31) - var2) * 3125) // var1
    var1 = (coeffs["p9"] * (p >> 13) * (p >> 13)) >> 25
    var2 = (coeffs["p8"] * p) >> 19
    p = ((p + var1 + var2) >> 8) + (coeffs["p7"] << 4)
    return p / 25600.0


def _bme280_compensate_hum(coeffs, t_fine, adc_h):
    var_h = t_fine - 76800.0
    var_h = (
        adc_h
        - (coeffs["h4"] * 64.0 + coeffs["h5"] / 16384.0 * var_h)
    ) * (
        coeffs["h2"] / 65536.0
        * (
            1.0
            + coeffs["h6"] / 67108864.0 * var_h
            * (1.0 + coeffs["h3"] / 67108864.0 * var_h)
        )
    )
    var_h = var_h * (1.0 - coeffs["h1"] * var_h / 524288.0)
    if var_h > 100.0:
        var_h = 100.0
    elif var_h < 0.0:
        var_h = 0.0
    return var_h


def _read_bme280(i2c, addr, coeffs):
    raw = i2c.readfrom_mem(addr, 0xF7, 8)
    adc_p = (raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4)
    adc_t = (raw[3] << 12) | (raw[4] << 4) | (raw[5] >> 4)
    adc_h = (raw[6] << 8) | raw[7]
    t_fine, temp_c = _bme280_compensate_temp(coeffs, adc_t)
    pressure_kpa = _bme280_compensate_press(coeffs, t_fine, adc_p)
    hum_pct = _bme280_compensate_hum(coeffs, t_fine, adc_h)
    return temp_c, hum_pct, pressure_kpa


def _build_payload(temp_c, hum_pct, lux, pressure_kpa, vsys_mv):
    if temp_c >= 0:
        temp_u8 = min(int(temp_c), 254)
    else:
        temp_u8 = PAYLOAD_INVALID_U8
    if hum_pct >= 0:
        hum_u8 = min(int(hum_pct), 254)
    else:
        hum_u8 = PAYLOAD_INVALID_U8
    if lux >= 0:
        lux_u16 = max(0, min(int(round(lux)), 65534))
    else:
        lux_u16 = PAYLOAD_INVALID_U16
    if pressure_kpa >= 0:
        pressure_hpa = max(0, min(int(round(pressure_kpa * 10.0)), 65534))
    else:
        pressure_hpa = PAYLOAD_INVALID_U16
    if vsys_mv >= 0:
        vsys_u16 = max(0, min(int(vsys_mv), 65534))
    else:
        vsys_u16 = PAYLOAD_INVALID_U16
    return struct.pack(
        PAYLOAD_FMT,
        temp_u8,
        hum_u8,
        lux_u16,
        pressure_hpa,
        vsys_u16,
    )


def _should_uplink(temp_c, hum_pct, lux, pressure_kpa):
    bme_ok = temp_c >= 0 or hum_pct >= 0 or pressure_kpa >= 0
    return bme_ok or lux >= 0


def _read_sensors(i2c, bme_addr, bme_coeffs):
    t_c, h_pct, pressure_kpa = -1, -1, -1.0
    if bme_coeffs is not None:
        try:
            t_c, h_pct, pressure_kpa = _read_bme280(i2c, bme_addr, bme_coeffs)
        except OSError:
            t_c, h_pct, pressure_kpa = -1, -1, -1.0
    try:
        lux = _read_bh1750_lux(i2c)
    except OSError:
        lux = -1.0
    vsys_mv = read_batt_mv(VSYS_SAMPLE_COUNT)
    return t_c, h_pct, pressure_kpa, lux, vsys_mv


def _print_sensors(t_c, h_pct, pressure_kpa, lux, vsys_mv):
    _log(
        "Sensors:",
        "BME280 temp_C=", t_c,
        "hum_%=", h_pct,
        "kPa=", round(pressure_kpa, 2) if pressure_kpa >= 0 else pressure_kpa,
        "BH1750 lux=", round(lux, 1) if lux >= 0 else lux,
        "VSYS mV=", vsys_mv if vsys_mv >= 0 else vsys_mv,
    )


def _pulse_onboard_led(led):
    led.on()
    time.sleep_ms(LED_PULSE_MS)
    led.off()


# =============================================================================
# LoRaWAN UART helpers
# =============================================================================

def _lora_flush_rx(uart):
    while uart.any():
        uart.read(uart.any())


def _lora_uart_text(buf):
    if not buf:
        return ""
    raw = "".join(chr(b & 0xFF) for b in buf)
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    parts = []
    for seg in raw.split("\n"):
        s = seg
        while s and ord(s[-1]) in (0, 255):
            s = s[:-1]
        while s and ord(s[0]) in (0, 255):
            s = s[1:]
        s = s.strip()
        if s:
            parts.append(s)
    return "\n".join(parts)


def _lora_exchange(uart, cmd, timeout_ms=LORA_CMD_TIMEOUT_MS, idle_break_ms=80):
    _lora_flush_rx(uart)
    line = cmd.strip("\r\n")
    _log("LoRa TX:", line)
    uart.write((line + "\r\n").encode())
    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    buf = bytearray()
    idle_start = None
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if uart.any():
            chunk = uart.read()
            if chunk:
                buf.extend(chunk)
            idle_start = None
            time.sleep_ms(5)
            continue
        if buf:
            if idle_start is None:
                idle_start = time.ticks_ms()
            elif time.ticks_diff(time.ticks_ms(), idle_start) >= idle_break_ms:
                break
        time.sleep_ms(10)
    if buf:
        _log("LoRa RX:", _lora_uart_text(buf))
    else:
        _log("LoRa RX: <no bytes within %d ms>" % timeout_ms)
    _lora_flush_rx(uart)
    return bytes(buf)


def _lora_hex_field(label, value, nbytes):
    h = value.strip().lower().replace(" ", "").replace(":", "")
    if len(h) != nbytes * 2:
        raise ValueError("%s: expected %d hex digits (%d bytes)" % (label, nbytes * 2, nbytes))
    int(h, 16)
    return h


def _lora_parse_plus_field(txt, name):
    """Parse +NAME:value or +NAME=value from modem response."""
    prefix = "+" + name.upper()
    for line in txt.replace("\r", "\n").split("\n"):
        line = line.strip()
        u = line.upper()
        if u.startswith(prefix + ":") or u.startswith(prefix + "="):
            return line.split(":", 1)[-1].split("=", 1)[-1].strip()
    return None


def _lora_dulstat_value(txt):
    for line in txt.replace("\r", "\n").split("\n"):
        line = line.strip().upper()
        if line.startswith("+DULSTAT:"):
            part = line.split(":", 1)[1].strip()
            if part.isdigit():
                return int(part)
    return None


def _lora_is_joined(txt):
    stat = _lora_dulstat_value(txt)
    return stat is not None and 1 <= stat <= 8


def _lora_query_joined(uart):
    raw = _lora_exchange(uart, "AT+DULSTAT?", timeout_ms=LORA_CMD_TIMEOUT_MS)
    txt = _lora_uart_text(raw)
    stat = _lora_dulstat_value(txt)
    if stat is not None:
        _log("LoRa: +DULSTAT:%02d" % stat)
    return _lora_is_joined(txt)


def _lora_clpm_ok(txt):
    return "+CME ERROR" not in txt.upper()


def _lora_enter_sleep(uart):
    raw = _lora_exchange(uart, "AT+CLPM=1", timeout_ms=LORA_CMD_TIMEOUT_MS)
    txt = _lora_uart_text(raw)
    if _lora_clpm_ok(txt):
        _log("LoRa: CLPM sleep OK")
        return True
    _log("LoRa: CLPM sleep rejected:", txt)
    return False


def _lora_wake(uart):
    """Wake A660 from CLPM via UART; do not require joined state."""
    _lora_flush_rx(uart)
    uart.write(b"\r\n\r\n")
    time.sleep_ms(100)
    _lora_flush_rx(uart)
    raw = _lora_exchange(uart, "AT+CLPM=0", timeout_ms=LORA_CMD_TIMEOUT_MS)
    txt = _lora_uart_text(raw)
    if not _lora_clpm_ok(txt):
        _log("LoRa: CLPM wake rejected:", txt)
        return False
    _log("LoRa: CLPM wake OK")
    return True


def _lora_standalone_fail_line(txt):
    u = txt.upper()
    return "+CME ERROR" in u or "DJOIN:FAIL" in u or "+DJOIN:FAIL" in u


def _lora_set_crxp(uart):
    raw = _lora_exchange(
        uart,
        "AT+CRXP=" + LORA_CRXP_PARAMS,
        timeout_ms=LORA_CMD_TIMEOUT_MS,
    )
    txt = _lora_uart_text(raw)
    if "+CME ERROR" in txt.upper():
        _log("LoRa: CRXP rejected — using modem defaults:", txt)
        return False
    return True


def _lora_uplink_failed(txt):
    u = txt.upper()
    return "ERR+SEND" in u or "+CME ERROR" in u


def _lora_uplink_ok(txt):
    u = txt.upper()
    return "OK+SEND" in u or "OK+SENT" in u or "OK+DEND" in u


def _lora_configure_common(uart):
    """Region / class / power / FPort — shared by OTAA and ABP."""
    _lora_exchange(uart, "AT+CCLASS=0", timeout_ms=LORA_CMD_TIMEOUT_MS)
    _lora_exchange(uart, "AT+RREGION=%d" % LORA_REGION, timeout_ms=LORA_CMD_TIMEOUT_MS)
    _lora_exchange(uart, "AT+RMAXTXP=%d" % LORA_MAX_TX_POWER, timeout_ms=LORA_CMD_TIMEOUT_MS)
    _lora_set_crxp(uart)
    _lora_exchange(uart, "AT+CAPPPORT=%d" % LORA_APP_FPORT, timeout_ms=LORA_CMD_TIMEOUT_MS)


def _lora_configure_otaa(uart, device, reboot=False):
    if reboot:
        time.sleep_ms(LORA_BOOT_SETTLE_MS)
        _lora_flush_rx(uart)
        _lora_exchange(uart, "AT+IREBOOT=1", timeout_ms=LORA_CMD_TIMEOUT_MS)
        time.sleep_ms(LORA_BOOT_SETTLE_MS)
    _lora_configure_common(uart)
    _lora_exchange(uart, "AT+CJOINMODE=0", timeout_ms=LORA_CMD_TIMEOUT_MS)
    _lora_exchange(uart, "AT+CDEVEUI=" + device["deveui"], timeout_ms=LORA_CMD_TIMEOUT_MS)
    _lora_exchange(uart, "AT+CAPPEUI=" + device["appeui"], timeout_ms=LORA_CMD_TIMEOUT_MS)
    _lora_exchange(uart, "AT+CAPPKEY=" + device["appkey"], timeout_ms=LORA_CMD_TIMEOUT_MS)


def _lora_query_session_keys(uart):
    """After OTAA join: read DevAddr / AppSKey / NwkSKey from modem."""
    raw = _lora_exchange(uart, "AT+CDEVADDR?", timeout_ms=LORA_CMD_TIMEOUT_MS)
    devaddr = _lora_parse_plus_field(_lora_uart_text(raw), "CDEVADDR")
    raw = _lora_exchange(uart, "AT+CAPPSKEY?", timeout_ms=LORA_CMD_TIMEOUT_MS)
    appskey = _lora_parse_plus_field(_lora_uart_text(raw), "CAPPSKEY")
    raw = _lora_exchange(uart, "AT+CNWKSKEY?", timeout_ms=LORA_CMD_TIMEOUT_MS)
    nwkskey = _lora_parse_plus_field(_lora_uart_text(raw), "CNWKSKEY")
    if not devaddr or not appskey or not nwkskey:
        _log("LoRa: key query incomplete")
        return None
    try:
        return {
            "devaddr": _lora_hex_field("devaddr", devaddr, 4),
            "appskey": _lora_hex_field("appskey", appskey, 16),
            "nwkskey": _lora_hex_field("nwkskey", nwkskey, 16),
            "fcnt": 0,
        }
    except ValueError as e:
        _log("LoRa: key parse failed", e)
        return None


def _lora_restore_abp(uart, session):
    """Inject ABP session from flash; returns True if modem reports joined."""
    _log("LoRa: restoring ABP session")
    _lora_configure_common(uart)
    _lora_exchange(uart, "AT+CJOINMODE=1", timeout_ms=LORA_CMD_TIMEOUT_MS)
    _lora_exchange(uart, "AT+CDEVADDR=" + session["devaddr"], timeout_ms=LORA_CMD_TIMEOUT_MS)
    _lora_exchange(uart, "AT+CAPPSKEY=" + session["appskey"], timeout_ms=LORA_CMD_TIMEOUT_MS)
    _lora_exchange(uart, "AT+CNWKSKEY=" + session["nwkskey"], timeout_ms=LORA_CMD_TIMEOUT_MS)
    _lora_exchange(uart, "AT+CSAVE", timeout_ms=LORA_CMD_TIMEOUT_MS)
    time.sleep_ms(200)
    return _lora_query_joined(uart)


def _lora_otaa_join(uart, onboard_led=None):
    cmd = "AT+DJOIN=" + LORA_DJOIN_PARAMS
    raw = _lora_exchange(uart, cmd, timeout_ms=10000)
    txt = _lora_uart_text(raw)
    if _lora_standalone_fail_line(txt):
        _log("LoRa: DJOIN rejected:", txt)
        return False
    deadline = time.ticks_add(time.ticks_ms(), LORA_JOIN_TIMEOUT_MS)
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if _lora_query_joined(uart):
            _log("LoRa: OTAA join complete")
            if onboard_led is not None:
                _pulse_onboard_led(onboard_led)
            return True
        time.sleep_ms(LORA_JOIN_POLL_MS)
    _log("LoRa: join timeout")
    return False


def _print_join_confirm_payload(payload, joined, confirm):
    if not DEBUG_LOG:
        return
    h = payload.hex().upper()
    n = len(payload)
    print("")
    print("=== Join confirm uplink ===")
    print("  joined:   ", joined)
    print("  fPort:    ", LORA_APP_FPORT)
    print("  confirm:  ", confirm)
    print("  hex:      ", payload.hex())
    print(
        "  AT cmd:   AT+DTRX=%d,%d,%d,%s"
        % (confirm, LORA_DTRX_NB_TRIALS, n, h)
    )
    print("")


def _print_uplink_payload(payload, joined, confirm=LORA_DTRX_CONFIRM):
    if not DEBUG_LOG:
        return
    temp_u8, hum_u8, lux_u16, pressure_hpa, vsys_u16 = struct.unpack(">BBHHH", payload)
    h = payload.hex().upper()
    n = len(payload)
    print("")
    print("=== Uplink send ===")
    print("  joined:   ", joined)
    print("  fPort:    ", LORA_APP_FPORT)
    print("  confirm:  ", confirm)
    print("  hex:      ", payload.hex())
    print("  temp:     ", temp_u8 if temp_u8 != PAYLOAD_INVALID_U8 else "invalid", "C")
    print("  hum:      ", hum_u8 if hum_u8 != PAYLOAD_INVALID_U8 else "invalid", "%RH")
    print("  lux:      ", lux_u16 if lux_u16 != PAYLOAD_INVALID_U16 else "invalid")
    print(
        "  pressure: ",
        "%.1f hPa" % (pressure_hpa / 10) if pressure_hpa != PAYLOAD_INVALID_U16 else "invalid",
    )
    print(
        "  vsys:     ",
        "%d mV" % vsys_u16 if vsys_u16 != PAYLOAD_INVALID_U16 else "invalid",
    )
    print(
        "  AT cmd:   AT+DTRX=%d,%d,%d,%s"
        % (confirm, LORA_DTRX_NB_TRIALS, n, h)
    )
    print("")


def _lora_send_dtrx(uart, body, onboard_led=None, confirm=LORA_DTRX_CONFIRM, label="uplink"):
    joined = _lora_query_joined(uart)
    if not joined:
        _log("LoRa: skip send — not joined (+DULSTAT:00)")
        return False
    if label == "join confirm":
        _print_join_confirm_payload(body, joined, confirm)
    else:
        _print_uplink_payload(body, joined, confirm)
    n = len(body)
    h = body.hex().upper()
    cmd = "AT+DTRX=%d,%d,%d,%s" % (confirm, LORA_DTRX_NB_TRIALS, n, h)
    raw = _lora_exchange(
        uart,
        cmd,
        timeout_ms=LORA_SEND_TIMEOUT_MS,
        idle_break_ms=LORA_DTRX_IDLE_MS,
    )
    txt = _lora_uart_text(raw)
    if not raw:
        _log("LoRa: uplink FAIL — no UART response")
        return False
    if _lora_uplink_failed(txt):
        _log("LoRa: uplink FAIL — rejected:", txt)
        return False
    if not _lora_uplink_ok(txt):
        _log("LoRa: uplink FAIL — ack missing:", txt)
        return False
    _log("LoRa: %s OK" % label)
    if onboard_led is not None:
        _pulse_onboard_led(onboard_led)
    return True


def _send_join_confirm_uplink(uart, onboard_led):
    if not _lora_query_joined(uart):
        return False
    _log("LoRa: join confirm delay %d s..." % LORA_JOIN_CONFIRM_DELAY_S)
    time.sleep(LORA_JOIN_CONFIRM_DELAY_S)
    if not _lora_query_joined(uart):
        return False
    return _lora_send_dtrx(
        uart,
        LORA_JOIN_CONFIRM_PAYLOAD,
        onboard_led,
        confirm=LORA_JOIN_CONFIRM_DTRX_CONFIRM,
        label="join confirm",
    )


def _ensure_lorawan_session(uart, onboard_led):
    """
    Prefer live modem session; else ABP from session.json; else OTAA.
    OTAA requires device.json on the Pico filesystem.
    Returns (joined_ok, session_dict_or_None).
    """
    _lora_wake(uart)

    if _lora_query_joined(uart):
        _log("LoRa: live session still joined")
        return True, session_load()

    session = session_load()
    if session is not None:
        if _lora_restore_abp(uart, session):
            _log("LoRa: ABP restore OK")
            return True, session
        _log("LoRa: ABP restore failed — clearing session")
        session_clear()

    session_clear()
    device = device_load()
    if device is None:
        _log("LoRa: missing/invalid", DEVICE_PATH, "— cannot OTAA")
        return False, None

    _lora_configure_otaa(uart, device, reboot=True)
    if not _lora_otaa_join(uart, onboard_led=onboard_led):
        return False, None

    keys = _lora_query_session_keys(uart)
    if keys is None:
        _log("LoRa: OTAA OK but key extract failed")
        return True, None
    session_save(keys["devaddr"], keys["nwkskey"], keys["appskey"], 0)
    _lora_exchange(uart, "AT+CSAVE", timeout_ms=LORA_CMD_TIMEOUT_MS)
    _send_join_confirm_uplink(uart, onboard_led)
    return True, keys


def _go_to_deepsleep(board, uart, i2c, bme_addr, sleep_ms):
    _power_down_sensors(i2c, bme_addr)
    try:
        _lora_enter_sleep(uart)
    except Exception:
        pass
    onboard = Pin("LED", Pin.OUT)
    onboard.off()
    board.go_deepsleep(sleep_ms, uart=uart, disable_usb=not DEBUG_USB)


# =============================================================================
# Main — single shot then deepsleep
# =============================================================================

def main():
    board = Board()
    i2c = board.sensor2_i2c
    uart = board.sensor3_lora_uart

    if DEBUG_I2C_SCAN:
        _log("I2C devices:", [hex(x) for x in i2c.scan()])

    onboard_led = Pin("LED", Pin.OUT)
    onboard_led.off()

    bme_addr = _bme280_detect_addr(i2c)
    bme_coeffs = None
    if bme_addr is not None:
        try:
            bme_coeffs = _bme280_init(i2c, bme_addr)
            _log("BME280 init OK at", hex(bme_addr))
        except OSError:
            _log("BME280 init failed")
            bme_coeffs = None
    else:
        _log("BME280 not found")

    joined, session = _ensure_lorawan_session(uart, onboard_led)
    if not joined:
        _log("LoRa: not joined — sleeping then retry")
        _go_to_deepsleep(board, uart, i2c, bme_addr, LORA_FAIL_RETRY_SLEEP_MS)
        return

    t_c, h_pct, pressure_kpa, lux, vsys_mv = _read_sensors(i2c, bme_addr, bme_coeffs)
    _print_sensors(t_c, h_pct, pressure_kpa, lux, vsys_mv)

    tx_ok = False
    if _should_uplink(t_c, h_pct, lux, pressure_kpa):
        payload = _build_payload(t_c, h_pct, lux, pressure_kpa, vsys_mv)
        tx_ok = _lora_send_dtrx(uart, payload, onboard_led, label="telemetry")
        if not tx_ok:
            _log("LoRa: telemetry failed — clearing session for next OTAA")
            session_clear()
            session = None
    else:
        _log("Uplink skipped (all sensors failed)")

    if tx_ok:
        if session is not None:
            session_bump_fcnt(session)
        elif session_load() is not None:
            session_bump_fcnt(session_load())

    _go_to_deepsleep(board, uart, i2c, bme_addr, SLEEP_TIME_MS)


if __name__ == "__main__":
    main()
