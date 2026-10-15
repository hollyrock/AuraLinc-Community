# EcoCONNECT 技術資料

## 構成とスペック

EcoCONNECTはメインボード、STEAM ボードで構成されています。
アルカリ乾電池3本、またはUSB電源で稼働し、複数の自由に使用できるコネクタ線を搭載するIoTデバイスです。

![summary](/images/docs/pict-main-board-summary.png)

### スペック

| MPU   | Raspberry Pi Pico2          |
| ----- | --------------------------- |
| データ通信 | LoRaWAN（A660-900T22）        |
| 開発言語  | MicroPython                 |
| センサー  | 気温/湿度/気圧（BME280）、照度（BH1750） |
| 電源    | アルカリ乾電池3本                   |

### メインボード

#### 概要

メインボードは各センサーデバイスからのデータを処理し、データを送信する4層基板のボードです。
MPUにはRaspberry Pi Pico2を使用し、LoRaWANモジュール（A660-900T22）とシリアル通信で接続されています。
また、I2Cバスを使用してSTEAMボードのセンサーとデータ通信をします。

LoRaWANモジュール（A660-900T22）はモジュール単体、または評価版モジュールのどちらかを搭載できます。
LoRaWANの動作を確認したい場合には、ピンヘッダーを使用して評価モジュールを搭載するとデバッグがスムーズにできます。

#### ピンアサイン

各コネクタの役割とピンアサインです。STEAMボードを使用する場合は、J1/J2コネクタが使用されます。
拡張用コネクタ(J4/6)のピンは自由に使用できます。
ファームウェアアップデート用コネクタ（J7）はLoRaWANモジュールのファームウェアを更新する際に使用します。
アドオンボード用コネクタ（J5/8）のピンは予約ピンで、将来の拡張ように使用されます。

| コネクタ名 | ピンアサイン | 用途 |
| -------- | ---------- | ---- |
| J1 | 1 : GND<br>2 : VBAT sens.<br>3 : VBAT <br>　4 : Reserve | バッテリに接続                               |
| J2 | 1 : SCL<br>3 : SDA<br>5 : 3V3<br>2/4/6/7/8 : GND | STEAMボードに接続 |
| J4 | 1 : VBUS<br>2 : 3V3_EN<br>3 : 3V3<br>4 : ADC_VREF<br>5 : AGND<br>6 : GPIO19<br>7 : GPIO18<br>8 : GPIO17 | 拡張用コネクタ<br>（Raspberry Pi Picoの各ピンに接続） |
| J5/J8 | 1 : GPIO16<br>4 : VSYS<br>6 : J8 P4<br>7 : J8 P5<br>10 : J8 P1<br>2/3/5/8/9/11/12 : GND | アドオンボード（予定）用 |
| J6 | 1 : GPIO2<br>2 : GPIO4<br>3 : GPIO5<br>4 : GPIO6<br>5 : GPIO7<br>6 : GPIO8<br>7 : GPIO9<br>8 : GPIO10<br>9 : GPIO11<br>10 : GPIO12 <br>11 : GPIO13<br>12 : GPIO15 | 拡張用コネクタ<br>（Raspberry Pi Picoの各ピンに接続） |
| J7    | 1 : VCC<br>2 : CTS<br>3 : SETB<br>4 : GND<br>5 : TXG<br>6 : XRES | ファームウェアアップデート（A660-900T）用 |

#### 物理スペックとコネクタの位置

![main board](/images/docs/main-board.png)

### STEAMボード

#### 概要

環境センサー（温度・湿度・環境光・気圧）を搭載した４層基板で構成されています。各センサーは1本のI2CバスでMPUと通信します。

想定される搭載センサーはBME280（温湿度、気圧）とBH1750（照度）で、BME280は基板表面、BH1750は基板裏面に搭載します。

プルアップレジスタ（R1/2）は使用するセンサーモジュールに搭載されない場合に適宜追加してください。

#### ピンアサイン

| コネクタ名 | ピンアサイン | 用途 |
| -------- | ---------- | ---- |
| J1 | 1 : SDA<br>3 : SCL<br>5 : 3V3<br>2/4/6/7/8 : GND | メインボードに接続 |
| J2 | 1 : ADDR<br>2 : SDA<br>3 : SCL<br>4 : GND<br>5 : 3V3 | BH1750（基板裏面）<br>に接続 |
| J3 | 1 : SDO<br>2 : SCL<br>3 : SDA<br>4 : CSR<br>5 : GND<br>6 : Vcore<br>7 : VIO | BME280（基板表面）<br>に接続 |

#### 物理スペックとコネクタの位置

![steam board](/images/docs/steam-board.png)
