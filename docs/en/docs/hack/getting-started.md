# Let’s get started

Welcome!
This page takes you, in about 15–20 minutes, to **reading sensor data with EcoCONNECT**.

## You will need

- An EcoCONNECT main board (assembled)
- A Micro-USB cable
- A computer (Windows / macOS / Linux)

## Steps

### 1. Connect the EcoCONNECT main board to your PC

Connect the EcoCONNECT main board to the PC with a Micro-USB cable. When it connects, the power LED blinks once.
[Where the EcoCONNECT connectors are](#)

### 2. Flash the ready-made firmware

EcoCONNECT includes a **firmware image** you can use without writing code first.

1. Open `firmware/pico2/release/` in the repository.
2. Follow the README in `firmware/pico2/` and copy the `.uf2` onto the Raspberry Pi Pico.
3. When the board reboots, you are ready for the first reading.

::: tip
Do not unplug the USB cable while flashing.
:::

### 3. Read the sensor values

Open a terminal and run the sensor-reading program.

### 4. Going further

You can now use sensor values on your PC.
Next: [Send data wirelessly](/en/docs/hack/remote).

## Other resources

- A [recipe](/en/steam/recipes) you can finish in about 10 minutes
- [Examples](/en/steam/examples) for ideas
- For teachers: [Workshop materials](/en/steam/)
