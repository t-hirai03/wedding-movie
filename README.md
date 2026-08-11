# wedding-movie

写真フォルダから Final Cut Pro 用の FCPXML（スライドショー）を生成するスクリプト。

## 必要なもの

- Python 3
- ffmpeg / ffprobe（`brew install ffmpeg`）
- Final Cut Pro

## 使い方

```bash
python3 build_fcpxml.py photos \
  -o out/movie.fcpxml \
  --project "結婚式ムービー" \
  --event "2026-07-26" \
  --library ~/Movies/結婚式.fcpbundle \
  --duration 5 \
  --transition 1 \
  --ken-burns 0.12 \
  --conform fill
```

生成した `.fcpxml` を Final Cut Pro で開くと、指定ライブラリに新規プロジェクトとして取り込まれる。

| オプション | 意味 |
|---|---|
| `--duration` | 写真1枚あたりの表示秒数 |
| `--transition` | トランジション秒数（0で無効） |
| `--ken-burns` | ゆっくりズームの量（0で無効） |
| `--conform` | `fill`（画面いっぱい・端が切れる）/ `fit`（全体表示・余白）/ `none` |
| `--format` | `1080p30` / `1080p2997` / `1080p24` / `4k30` |
| `--assets-only` | プロジェクトを作らず、イベントに素材クリップだけ読み込む |
| `--keyword` | 各クリップに付けるキーワード（キーワードコレクションになる） |

## 素材だけ読み込む

タイムラインを作らず、写真をイベントの素材として入れるだけの場合。

```bash
python3 build_fcpxml.py photos \
  -o out/assets_only.fcpxml \
  --event "wedding-movie" \
  --library ~/Movies/結婚式.fcpbundle \
  --assets-only \
  --keyword "画像データ"
```

Final Cut のフォルダにはクリップを入れられないため、まとめたい場合は `--keyword` を使う。同名のキーワードコレクション（サイドバーの鍵マーク）が作られ、そこに全クリップが入る。

イベント名は**ASCIIで指定する**こと。日本語名だと既存イベントに一致せず `名前 2` が新規作成される。詳細は [.claude/rules/final-cut.md](./.claude/rules/final-cut.md) を参照。

## 検証

Final Cut Pro 本体に同梱されている DTD で検証できる。DTD は Apple の著作物なのでリポジトリには含めていない。

```bash
cp "/Applications/Final Cut Pro.app/Contents/Frameworks/Interchange.framework/Versions/A/Resources/FCPXMLv1_13.dtd" .
xmllint --noout --dtdvalid FCPXMLv1_13.dtd out/movie.fcpxml
```

## 素材について

`photos/` と `out/`、Final Cut のライブラリは `.gitignore` で除外している。
写真は顔が識別できる個人情報にあたるため、リポジトリにコミットしない。

## 未確認の項目

- トランジション（`<transition>`）が取り込み時に適用されるか
- Ken Burns（`adjust-transform` のキーフレーム）が反映されるか

いずれも Final Cut 側の正確な記述形式が未確認。
Final Cut で手動設定したプロジェクトを FCPXML 書き出しして、実際の形式を確認する必要がある。
