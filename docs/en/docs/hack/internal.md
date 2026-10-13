# EcoCONNECT technical notes

## Structure and specifications

EcoCONNECT is made of a main board and a STEAM board.
It runs on three alkaline batteries or USB power, and it is an IoT device with several connector wires you can use freely.

![summary](/images/hacks/pict-main-board-summary.png)

### Specifications

| Item | Value |
| --- | --- |
| MPU | Raspberry Pi Pico 2 |
| Data communication | LoRaWAN (A660-900T22) |
| Development language | MicroPython |
| Sensors | Temperature / humidity / pressure (BME280), illuminance (BH1750) |
| Power | Three alkaline batteries |

### Main board

#### Overview

The main board processes data from each sensor device and sends that data. It is a four-layer board.
The MPU is a Raspberry Pi Pico 2, connected to the LoRaWAN module (A660-900T22) by serial communication.
It also talks to the sensors on the STEAM board over an I2C bus.

The LoRaWAN module (A660-900T22) can be fitted either as the module alone or as the evaluation module.
To check LoRaWAN behavior, mount the evaluation module on pin headers. Debugging is smoother that way.

#### Pin assignment

Role and pin assignment of each connector. When you use the STEAM board, connectors J1 and J2 are used.
Pins on the expansion connectors (J4 and J6) are free to use.
The firmware-update connector (J7) is used when updating the LoRaWAN module firmware.
Pins on the add-on board connectors (J5 and J8) are reserved for future expansion.

| Connector | Pin assignment | Use |
| --- | --- | --- |
| J1 | 1 : GND<br>2 : VBAT sens.<br>3 : VBAT<br>4 : Reserve | Connect to the battery |
| J2 | 1 : SCL<br>3 : SDA<br>5 : 3V3<br>2/4/6/7/8 : GND | Connect to the STEAM board |
| J4 | 1 : VBUS<br>2 : 3V3_EN<br>3 : 3V3<br>4 : ADC_VREF<br>5 : AGND<br>6 : GPIO19<br>7 : GPIO18<br>8 : GPIO17 | Expansion connector<br>(connected to Raspberry Pi Pico pins) |
| J5/J8 | 1 : GPIO16<br>4 : VSYS<br>6 : J8 P4<br>7 : J8 P5<br>10 : J8 P1<br>2/3/5/8/9/11/12 : GND | For a planned add-on board |
| J6 | 1 : GPIO2<br>2 : GPIO4<br>3 : GPIO5<br>4 : GPIO6<br>5 : GPIO7<br>6 : GPIO8<br>7 : GPIO9<br>8 : GPIO10<br>9 : GPIO11<br>10 : GPIO12<br>11 : GPIO13<br>12 : GPIO15 | Expansion connector<br>(connected to Raspberry Pi Pico pins) |
| J7 | 1 : VCC<br>2 : CTS<br>3 : SETB<br>4 : GND<br>5 : TXG<br>6 : XRES | Firmware update (A660-900T) |

#### Physical layout and connector positions

![main board](/images/hacks/main-board.png)

### STEAM board

#### Overview

This is a four-layer board with environmental sensors (temperature, humidity, ambient light, and pressure). Each sensor talks to the MPU on one I2C bus.

The sensors expected on the board are the BME280 (temperature, humidity, and pressure) and the BH1750 (illuminance). Mount the BME280 on the front of the board and the BH1750 on the back.

Add pull-up resistors (R1 and R2) when the sensor module you use does not already include them.

#### Pin assignment

| Connector | Pin assignment | Use |
| --- | --- | --- |
| J1 | 1 : SDA<br>3 : SCL<br>5 : 3V3<br>2/4/6/7/8 : GND | Connect to the main board |
| J2 | 1 : ADDR<br>2 : SDA<br>3 : SCL<br>4 : GND<br>5 : 3V3 | Connect to the BH1750<br>(back of the board) |
| J3 | 1 : SDO<br>2 : SCL<br>3 : SDA<br>4 : CSR<br>5 : GND<br>6 : Vcore<br>7 : VIO | Connect to the BME280<br>(front of the board) |

#### Physical layout and connector positions

![steam board](/images/hacks/steam-board.png)
