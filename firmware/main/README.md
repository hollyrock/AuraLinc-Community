# EcoCONNECT Control Code (MicroPython)

## What’s here

| Path | What it is |
| --- | --- |
| `device.json.example` | Configuration for LoRaWAN module |
| `hal_hardware.py` | HAL code for current device configuration |
| `main.py` | Main logic to measurement |

## Installation

1. Set each parameters (deveui, appeui, and appkey) for LoRa communications and rename file name from `device.json.example` to `device.json`.
2. Copy all 3 files onto pico2 via USB port.
