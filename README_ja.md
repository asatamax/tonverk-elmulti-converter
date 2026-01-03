🇬🇧 [English](README.md) | 🇯🇵 日本語

# elmconv

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: ISC](https://img.shields.io/badge/License-ISC-green.svg)](LICENSE)
[![Changelog](https://img.shields.io/badge/changelog-v1.1.1-orange.svg)](CHANGELOG.md)

マルチサンプルインストゥルメントを Elektron Tonverk 形式に変換します。

- ✓ **Logic Pro** — Auto Sampler エクスポート (EXS24)
- ✓ **SFZ ライブラリ** — 既存のコレクションを活用
- ✓ **フル機能** — クロスフェード付きループ、ベロシティレイヤー、ラウンドロビン対応

出力形式: `.elmulti` (Tonverk のネイティブマルチサンプル形式)

**[GUI版はこちら](README-GUI.md)** - コマンドライン不要！

## クイックスタート

```bash
# インストゥルメントを変換（Tonverk 用に自動的に 48kHz にリサンプリング）
python3 elmconv.py MyInstrument.exs output/
```

## 動作要件

- Python 3.8 以上
- ffmpeg

### ffmpeg のインストール

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# https://ffmpeg.org/download.html からダウンロード
# 注意: "essentials" ではなく "full" ビルドを使用（soxr リサンプラーが必要）
```

## 使い方

```bash
python3 elmconv.py INPUT_FILE [INPUT_FILE ...] OUTPUT_DIR [options]
```

### オプション

| オプション | 説明 |
|--------|-------------|
| `-N, --normalize [DB]` | WAV ファイルをピーク正規化（デフォルト: 0dB） |
| `-O, --optimize-loop` | リサンプリング後のループポイントを最適化してシームレスなループを実現 |
| `--loop-search-range N` | ループ最適化の検索範囲（デフォルト: 5 サンプル） |
| `--single-cycle-threshold N` | シングルサイクルとして扱う最大ループ長（デフォルト: 512、0 で無効化） |
| `--no-single-cycle` | シングルサイクル波形の検出を無効化 |
| `--no-embed-loop` | WAV ファイルにループ情報（smpl チャンク）を埋め込まない |
| `--round-loop` | ループポイント計算に int() ではなく round() を使用 |
| `-R, --resample-rate RATE` | 指定レートにリサンプリング（デフォルト: 48000 Hz） |
| `--no-resample` | 元のサンプルレートを維持（48kHz リサンプリングを無効化） |
| `--use-accurate-ratio` | 実際のファイル長からリサンプル比を計算 |
| `--prefix PREFIX` | インストゥルメント名とファイル名にプレフィックスを追加 |

### 使用例

```bash
# 基本的な変換（デフォルトで 48kHz にリサンプリング）
python3 elmconv.py MyInstrument.exs output/

# ループ最適化付き（ループサンプルに推奨）
python3 elmconv.py MyInstrument.sfz output/ -O

# 複数ファイルを一括変換
python3 elmconv.py /path/to/*.sfz output/ -O

# プレフィックスを追加して整理（例: 音源ごとに分類）
python3 elmconv.py MyInstrument.exs output/ -O --prefix "JV1010 - "

# 音量レベルを正規化
python3 elmconv.py MyInstrument.sfz output/ -O --normalize

# フルオプション: ループ最適化、プレフィックス、正規化
python3 elmconv.py MyInstrument.exs output/ -O --prefix "JV1010 - " -N

# 元のサンプルレートを維持（リサンプリング無効）
python3 elmconv.py MyInstrument.exs output/ --no-resample

# カスタムサンプルレート
python3 elmconv.py MyInstrument.exs output/ -R 44100
```

### 出力

コンバーターは各インストゥルメントごとにサブディレクトリを作成します：
- `InstrumentName.elmulti` - Tonverk マッピングファイル
- `*.wav` - 変換されたサンプル（24bit PCM）

## 機能

- ベロシティレイヤー
- ラウンドロビンサンプル
- クロスフェード付きループポイント
- **ループポイント最適化** - リサンプリング後のループポイントを自動調整してシームレスなループを実現
- **シングルサイクル波形検出** - 短いループ（シンセ波形）のピッチ精度を維持
- **smpl チャンク埋め込み** - ループ情報とキーセンターを WAV ファイルに埋め込み（デフォルトで有効）
- 高品質リサンプリング（SoX Resampler）
- SFZ トランスポーズ対応（キーセンター調整）

## 対応フォーマット

| フォーマット | 状態 |
|--------|--------|
| EXS24 (.exs) | 対応 |
| SFZ (.sfz) | 対応 |

## 制限事項

`.elmulti` 形式には EXS24/SFZ と比較していくつかの制限があります：

- **ベロシティクロスフェード** - 非対応（ハードスイッチのみ）
- **明示的なキーレンジ** - 非対応（Tonverk はピッチ間を自動補間）
- **サンプルレイヤリング** - 同一ノートに複数サンプルを重ねることは不可
- **ピンポンループ** - フォワードループのみ
- **ファインチューニング / パン** - elmulti 形式では非対応

## ドキュメント

詳細なフォーマット仕様は `docs/` ディレクトリを参照：

- [ELMULTI_FORMAT_SPEC.md](docs/ELMULTI_FORMAT_SPEC.md) - リバースエンジニアリングによる `.elmulti` フォーマット仕様
- [EXS24_FORMAT_SPEC.md](docs/EXS24_FORMAT_SPEC.md) - EXS24 バイナリフォーマットリファレンス
- [FORMAT_MAPPING.md](docs/FORMAT_MAPPING.md) - フォーマット間のフィールドマッピング

## ツール

`tools/` に追加ユーティリティがあります：

- **analyze_loops.py** - 変換したインストゥルメントのループポイント連続性を分析
- **loop_calculator.py** - サンプルレート変換と最適なループポイントを計算

詳細は [tools/README.md](tools/README.md) を参照。

## コントリビューション

Issue や Pull Request は歓迎です！問題や提案がありましたら、お気軽に Issue を作成してください。

## ライセンス

ISC License - [LICENSE](LICENSE) ファイルを参照。

vonred による [exs2sfz.py](https://gist.github.com/vonred/3965972) をベースにしています。

## 謝辞

- vonred - オリジナルの EXS24 パーサー
- [ConvertWithMoss](https://github.com/git-moss/ConvertWithMoss) - EXS24 フォーマットリファレンス
