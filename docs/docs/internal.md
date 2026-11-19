# EcoCONNECT 技術資料

## 概要

EcoCONNECTは本体（データ処理部）とSTEAMセンサーで構成されています。
アルカリ乾電池3本、またはUSB電源で稼働し、複数の自由に使用できるコネクタ線を搭載するIoTデバイスです。

![summary](/images/docs/pict-main-board-summary.png)

### スペック

| MPU   | Raspberry Pi Pico2          |
| ----- | --------------------------- |
| データ通信 | LoRaWAN（A660-900T22）        |
| 開発言語  | MicroPython                 |
| センサー  | 気温/湿度/気圧（BME280）、照度（BH1750） |
| 電源    | アルカリ乾電池3本                   |

## 構造

### 本体の構造

メインボードは各センサーデバイスからのデータを処理し、データを送信する4層基板のボードです。

MPUにはRaspberry Pi Pico2を使用し、LoRaWANモジュール（A660-900T22）とシリアル通信で接続されています。

また、I2Cバスを使用してSTEAMボードのセンサーとデータ通信をします。

LoRaWANモジュール（A660-900T22）はモジュール単体、または評価版モジュールのどちらかを搭載できます。

LoRaWANの動作を確認したい場合には、ピンヘッダーを使用して評価モジュールを搭載するとデバッグがスムーズにできます。

[本体回路図](#構造)

### STEAMセンサーの構造

環境センサー（温度・湿度・環境光・気圧）を搭載した４層基板で構成されています。各センサーは1本のI2CバスでMPUと通信します。

想定される搭載センサーはBME280とBH1750（下表参照）で、BME280は基板表面、BH1750は基板裏面に搭載します。

一覧以外のセンサーモジュールを使用する場合には、MPU側でI2Cのターゲットアドレスを変更し、必要な信号ピンを追加またはケーブル接続してください。

プルアップレジスタ（R1/2）は使用するセンサーモジュールのどちらにも搭載されない場合に追加してください。

| センサー | モジュール名 | 型番 |
| ------- | --------- | ---- |
| 温湿度・気圧センサモジュール | スイッチサイエンス BME280搭載 温湿度・気圧センサモジュール | SSCI-022361 |
| 照度センサモジュール | GY-302 BH1750光強度照明モジュール | GY-302 互換 |

[STEAMセンサー回路図](/pdf/sch-steam-board.pdf)

## コネクタ

### 本体にあるコネクタとピンアサイン

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

![main board](/images/docs/main-board.png)

### STEAMセンサーにあるコネクタとピンアサイン

| コネクタ名 | ピンアサイン | 用途 |
| -------- | ---------- | ---- |
| J1 | 1 : SDA<br>3 : SCL<br>5 : 3V3<br>2/4/6/7/8 : GND | メインボードに接続 |
| J2 | 1 : ADDR<br>2 : SDA<br>3 : SCL<br>4 : GND<br>5 : 3V3 | BH1750（基板裏面）<br>に接続 |
| J3 | 1 : SDO<br>2 : SCL<br>3 : SDA<br>4 : CSR<br>5 : GND<br>6 : Vcore<br>7 : VIO | BME280（基板表面）<br>に接続 |

![steam board](/images/docs/steam-board.png)

## ケーブル配線

EcoCONNECT（左側）とSTEAMセンサー（右側J1）は以下のように接続されます。

ケーブル長は30cm以下にします。

![steam board](/images/docs/steam-board-connection.png)
