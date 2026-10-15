# ファームウェアと制御コード

EcoCONNECTはカスタムモジュール（`firmware/pico2/`）を追加した MicroPythonと制御コード(`firmware/main/`)で動作します。

ここではカスタムモジュールや制御コードのインストール方法を紹介します。

## カスタムモジュールのインストール

Pico2用にリリースされているuf2イメージのパワーマネージメント機能を高めるため、EcoCONNECTでは、カスタムモジュールを組み込んだMicroPythonを使用しています。

### コンパイル済みのイメージをインストール

すぐに実行したい場合には、コンパイル済みのカスタムイメージをダウンロードして使用します。

1. [AuraLinc Communityのリポジトリ](https://github.com/hollyrock/AuraLinc-Community)にある`firmware/pico2/release`からファームウェア(`ecoconnect-pico2.uf2`)をダウンロードする。
2. USBケーブルを使用して、メインボードのUSBポート（MicroUSB）とPCを、メインボードのPico2上にある`BOOTSEL`ボタンを押しながら接続する。
3. PCのファイルマネージャを開き、`RP2350`フォルダが追加されたことを確認し、このフォルダにファームウェアをドラッグ＆ドロップする。
4. ファームウェア更新が完了するとメインボードが自動で再起動される。（PCでUSBデバイスの取り外し警告が出るがあるが無視して構わない）
5. USBケーブルをPCから抜き取り、ファームウェア更新完了。

ここまででカスタマイズされたMicroPythonを動作させる準備が整いました。
続けて下にある「制御コードのインストール」に進みます。

### ソースをコンパイルしたい場合（開発者向け）

ここではMicroPythonカスタムモジュールをビルドする手順を解説します。（macOS環境向け）
「コンパイル済みのイメージをインストール」した場合には、この章はスキップして構いません。

#### 手順1: 開発ツールのインストール（macOS）

Homebrewを利用して、ビルドに必要なCMakeやARMコンパイラをインストールします。

```bash
brew update
brew install cmake ninja gcc-arm-none-eabi git pkg-config
```

#### 手順2: MicroPythonソースの取得と準備

MicroPythonの公式リポジトリをクローンし、サブモジュールを初期化します。

```bash
git clone --recursive https://github.com/micropython/micropython.git
cd micropython
git submodule update --init

```

#### 手順3: カスタムCモジュールの準備

プロジェクトルートにカスタムモジュール用のディレクトリ（例: `my_module`）を作成し、Cコードとビルド設定を配置します。

AuraLincのカスタムモジュールをコンパイルする場合には、`firmware/pico2/auralinc_c_modules`をダウンロードし、カスタムモジュール用のディレクトリにします。

自作コードのためのサンプルとして、以下では与えられた値を2倍にして返すカスタムモジュール`my_module_double_val`を定義します。

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

#### 手順4: ビルドの実行

`ports/rp2` に移動し、CMakeを使ってビルドを行います。

```bash
cd ports/rp2
make submodules

mkdir -p build-pico2
cd build-pico2

# 絶対パスまたは相対パスで USERMOD_DIR を指定
cmake -DPICO_PLATFORM=rp2350 -DBOARD=RPI_PICO2 -DUSERMOD_DIR=../../my_module ..
make -j$(sysctl -n hw.ncpu)

```

ビルド完了後、`build-pico2/firmware.uf2` ファイルが生成されていることを確認します。

#### 手順5: カスタムファームウェアの書き込み

1. **ブートモード**: メインボードのRaspberry Pi Pico 2にある **BOOTSEL** ボタンを押しながらPCのUSBポートに接続します。
2. **転送**: マウントされた「RP2350」ドライブに、 `firmware.uf2` をドラッグ＆ドロップします（自動的に再起動します）。
3. **REPL確認**: `mpremote` などのシリアルツールで接続し、モジュールを検証します。

```bash
pip install mpremote
mpremote connect /dev/cu.usbmodem*

```

REPL上で次を実行して `84` が返れば成功です。
これで、カスタムモジュール`my_module_double_val`が実行できるファームウェアのできあがりです。

```python
>>> import my_module
>>> my_module.double_val(42)
84

```

## 制御コードのインストール

カスタムモジュール（auralinc_c_modules）が組み込まれているファームウェアを書き込んだら、センサーデータを送信する制御コードをインストールします。

### 手順１： 制御コードの準備

まず、`firmware/main`フォルダから以下のファイルをダウンロードします。

- `main.py`
- `hal_hardware.py`
- `device.json.example`

今回のLoRaWANの通信では、`deveui`, `appeui`, `appkey`を使用します。

`deveui`は購入したLoRaWANモジュールに固有のものです。購入時の添付されてきた紙などを確認します。

`appeui`, `appkey`は[The Things Networkに繋げてみよう](/docs/docs/ttn.md)で設定しますので、リンク先を参照してそれぞれの値を取得します。

３つすべての値が揃ったら`device.json.example`に書き込み、ファイル名を`device.json`に変更して保存します。

### 手順２： 制御コードの実行

メインボードをPCに接続し、先の`main.py`、 `hal_hardware.py`、`device.json.example`をマウントされたドライブ「RP2350」にコピーします。

コピーが完了したらメインボードをPCから取り外します。
メインボードは電源スイッチが入ると同時に、`main.py`を実行しデータ送信を開始します。
