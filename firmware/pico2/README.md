# EcoCONNECT firmware (Pico 2)

Souce codes and Ready-to-use firmware image for the EcoCONNECT main board.

## What’s here

| Path | What it is |
| --- | --- |
| `release/` | Firmware image(s) you can copy to the board |
| `auralinc_c_modules` | Source code |

## AuraLinc Pico2 Firmware

board_power — RP2350 POWMAN low-power sleep for MicroPython (user C module).
Uses Pico SDK hardware_powman to power down the switched core (and SRAM / XIP cache) and wake from the always-on timer.

Wake triggers a full chip reboot → MicroPython restarts → main.py runs from the top (same contract as machine.deepsleep on rp2, but far lower idle current than lightsleep).

Requires: MicroPython built for RPI_PICO2 / RP2350 with this usermod linked.

## Flash the board (beginner path)

1. Download the `.uf2` file from the `release/` folder in this directory.
2. Unplug the board’s USB cable.
3. Hold the **BOOTSEL** button on the Pico 2.
4. Plug in USB while still holding BOOTSEL, then release the button.
5. A drive named something like **RPI-RP2** appears on your computer.
6. Copy the `.uf2` file onto that drive.
7. The board reboots by itself — flashing is done.
