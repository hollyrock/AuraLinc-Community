# EcoCONNECT Community

[English](./README.en.md)

センサーで学ぶオープンソース・ハードウェアのコミュニティサイトです。初心者向けドキュメント、STEAM のアイデア、ファームウェア画像、オープンな基板設計を公開しています。hollyRock による EcoCONNECT プロジェクトです。

## サイトを見る

- **ドキュメント（GitHub Pages）:** https://hollyrock.github.io/AuraLinc-Community/
- **このリポジトリ**
  - `docs/` — 初心者向けドキュメント（日本語がデフォルト、英語は `/en/`）
  - `firmware/pico2/release/` — 書き込み用ファームウェア
  - `hardware/` — メインボード設計ファイル

## リポジトリ構成

```text
community/
├── docs/                      # ドキュメント（JA + EN）
├── firmware/pico2/release/    # 公開ファームウェア画像
├── hardware/                  # OSHWA 向けボードデータ
└── site/                      # ビルド済みサイト（GitHub Pages）
```

内部ソース、ビルド用モジュール、管理用スクリプトはローカルに留め、GitHub には公開していません。
