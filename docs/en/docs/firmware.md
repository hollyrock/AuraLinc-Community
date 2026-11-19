# Firmware and control code

EcoCONNECT runs MicroPython with a custom module added (`firmware/pico2/`) and the control code (`firmware/main/`).

This page shows how to install the custom module and the control code.

## Install the custom module

To improve the power management of the released Pico 2 uf2 image, EcoCONNECT uses a MicroPython build that includes a custom module.

### Install the precompiled image

If you want to get running right away, download and use the precompiled custom image.

1. Download the firmware (`ecoconnect-pico2.uf2`) from `firmware/pico2/release` in the [AuraLinc Community repository](https://github.com/hollyrock/AuraLinc-Community).
2. Hold the `BOOTSEL` button on the Pico 2 of the main board while you connect the main board's USB port (MicroUSB) to your PC with a USB cable.
3. Open the file manager on your PC, confirm that an `RP2350` folder has appeared, and drag and drop the firmware onto it.
4. When the firmware update finishes, the main board restarts automatically. (Your PC may show a warning that a USB device was removed. You can ignore it.)
5. Unplug the USB cable from the PC. The firmware update is done.

The customized MicroPython is now ready to run.
Continue with “Install the control code” below.

### Compile the source yourself (for developers)

This section explains how to build the MicroPython custom module. (For macOS.)
If you already installed the precompiled image, you can skip this section.

#### Step 1: Install development tools (macOS)

Use Homebrew to install CMake and the ARM compiler that the build needs.

```bash
brew update
brew install cmake ninja gcc-arm-none-eabi git pkg-config
```

#### Step 2: Get and prepare the MicroPython source

Clone the official MicroPython repository and initialize the submodules.

```bash
git clone --recursive https://github.com/micropython/micropython.git
cd micropython
git submodule update --init

```

#### Step 3: Prepare the custom C module

Create a directory for the custom module in the project root (for example, `my_module`) and put the C code and build settings in it.

To compile the AuraLinc custom module, download `firmware/pico2/auralinc_c_modules` and use it as the custom module directory.

As a sample for your own code, the following defines a custom module `my_module_double_val` that doubles the value it is given and returns it.

##### 1. `my_module/my_module.c`

```c
#include "py/runtime.h"

STATIC mp_obj_t my_module_double_val(mp_obj_t val_in) {
    mp_int_t val = mp_obj_get_int(val_in);
    return mp_obj_new_int(val * 2);
}
MP_DEFINE_CONST_FUN_OBJ_1(my_module_double_val_obj, my_module_double_val);

STATIC const mp_rom_map_elem_t my_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_my_module) },
    { MP_ROM_QSTR(MP_QSTR_double_val), MP_ROM_QSTR(&my_module_double_val_obj) },
};
STATIC MP_DEFINE_CONST_DICT(my_module_globals, my_module_globals_table);

const mp_obj_module_t my_module_user_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&my_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_my_module, my_module_user_module);

```

##### 2. `my_module/micropython.cmake`

```cmake
add_library(usermod_my_module INTERFACE)

target_sources(usermod_my_module INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/my_module.c
)

target_include_directories(usermod_my_module INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

```

#### Step 4: Run the build

Move to `ports/rp2` and build with CMake.

```bash
cd ports/rp2
make submodules

mkdir -p build-pico2
cd build-pico2

# Set USERMOD_DIR as an absolute or relative path
cmake -DPICO_PLATFORM=rp2350 -DBOARD=RPI_PICO2 -DUSERMOD_DIR=../../my_module ..
make -j$(sysctl -n hw.ncpu)

```

When the build finishes, confirm that `build-pico2/firmware.uf2` has been created.

#### Step 5: Write the custom firmware

1. **Boot mode**: Hold the **BOOTSEL** button on the Raspberry Pi Pico 2 of the main board while you connect it to a USB port on your PC.
2. **Transfer**: Drag and drop `firmware.uf2` onto the mounted “RP2350” drive (the board restarts automatically).
3. **Check the REPL**: Connect with a serial tool such as `mpremote` and verify the module.

```bash
pip install mpremote
mpremote connect /dev/cu.usbmodem*

```

Run the following in the REPL. If it returns `84`, it worked.
You now have firmware that can run the custom module `my_module_double_val`.

```python
>>> import my_module
>>> my_module.double_val(42)
84

```

## Install the control code

After you flash the firmware that includes the custom module (auralinc_c_modules), install the control code that sends sensor data.

### Step 1: Prepare the control code

First, download the following files from the `firmware/main` folder.

- `main.py`
- `hal_hardware.py`
- `device.json.example`

This LoRaWAN communication uses `deveui`, `appeui`, and `appkey`.

`deveui` is unique to the LoRaWAN module you bought. Check the paper that came with it.

You set `appeui` and `appkey` in [Connect to The Things Network](/en/docs/ttn), so follow that page to get each value.

When you have all three values, write them into `device.json.example`, save it, and rename the file to `device.json`.

### Step 2: Run the control code

Connect the main board to your PC and copy `main.py`, `hal_hardware.py`, and `device.json` to the mounted drive “RP2350”.

When the copy finishes, unplug the main board from the PC.
As soon as you switch the main board's power on, it runs `main.py` and starts sending data.
