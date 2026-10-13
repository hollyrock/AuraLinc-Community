# AuraLinc Community

[English](./README.en.md)

AuraLincのコミュニティサイトです。AuraLinc EcoCONNECTをオープンソースで公開しています。

## サイト構成

| セクション | 内容 |
| --- | --- |
| **ドキュメント** | はじめ方・チュートリアル・リポジトリ案内・FAQ |
| **ワークショップ資料** | ワークショップ用資料 |
| **コミュニティ広場** | アイデア・質問・提案（GitHub Discussions / giscus） |

- **サイト:** https://hollyrock.github.io/AuraLinc-Community/
- **Discussions:** https://github.com/hollyrock/AuraLinc-Community/discussions

```text
AuraLinc-Community/
├── docs/                   # Github Pages用ソース
│   ├── index.md
│   ├── community/          # アイデア・質問・提案
│   ├── docs/               # マニュアル・FAQ等
│   ├── en/                 # 英語表示用
│   ├── public/             # ロゴや共通オブジェクト
│   └── steam/              # ワークショップ用資料
├── firmware/
│   ├── EcoCONNECT/         # EcoCONNECT制御コード
│   └── pico2/
│       ├── release/        # Pico2 イメージ
│       └── src/            # Pico2 F/Wコード
├── hardware/
│   ├── main-board/         # メイン基板回路データ
│   │   └── libs/           # KiCADライブラリ
│   └── steam-board/        # STEAMセンサー基板回路データ
│       └── libs/           # KiCADライブラリ
└── site/                   # サイト本体
```

## ライセンス

本プロジェクトはコンポーネントごとに複数のライセンスが存在します。

- **ハードウェア デザイン** (`/hardware/`): [CERN-OHL-P-2.0](hardware/LICENSE-CERN-OHL-P.txt)
- **ファームウェア ソースコード** (`/firmware/`): [MIT License](firmware/LICENSE-MIT.txt)
- **ドキュメント & メディア** (`/docs/`): [CC-BY-4.0](docs/LICENSE-CC-BY.txt)

各フォルダに存在する`LICENSE`ファイルを参照してください。
