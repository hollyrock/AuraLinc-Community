# リポジトリ案内

この公開コミュニティリポジトリで見られるファイルの場所です。

## 公開しているもの

| フォルダ | 内容 |
| --- | --- |
| `docs/` | サイト用ドキュメント（日本語がデフォルト、英語は `/en/`） |
| `firmware/pico2/release/` | 書き込み用ファームウェア画像 |
| `firmware/pico2/README.md` | Raspberry Pi Pico への書き込み手順 |
| `hardware/main-board/` | メインボード設計ファイル（OSHWA 向け） |
| `hardware/main-board/libs/` | KiCad シンボル・フットプリント |

## すすめ方

1. [はじめ方](./getting-started) でボードを動かす
2. `firmware/pico2/README.md` で書き込みを確認する
3. 設計を見たくなったら `hardware/main-board/` を KiCad で開く

内部のビルド用ツールやアプリソースは、この公開リポジトリには含めていません。
