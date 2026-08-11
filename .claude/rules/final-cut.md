# Final Cut Pro ライブラリ規約

## ライブラリ

| 項目 | 値 |
|---|---|
| ライブラリ | `~/Movies/結婚式.fcpbundle` |
| アプリ本体 | `/Applications/Final Cut Pro Creator Studio.app`（`open -a "Final Cut Pro"` では見つからない） |
| Final Cut Pro | 12.3（FCPXMLは1.14まで対応。`build_fcpxml.py` は1.13を出力） |

## イベントの使い分け

| イベント | 用途 |
|---|---|
| `wedding-movie` | **本番。** 画像素材はここに入れる |
| `2026-07-26` | 検証用。FCPXML取り込みの動作確認 |
| `素材` | 素材置き場（現在空） |

## イベント名はASCIIにする（重要）

**日本語のイベント名を指定すると、既存イベントに一致せず `名前 2` が新規作成される。** `本番ムービー` を指定して `本番ムービー 2` が作られた。一方 ASCII の `2026-07-26` は既存イベントに正しく一致する。

イベント名・プロジェクト名はASCIIで付ける。

推測だが、macOSがファイル名をNFD（「ヒ」＋濁点）で保持するのに対しPythonが出力するXMLはNFC（「ビ」1文字）で、濁点を含む名前が別物として比較されている可能性がある。**未検証**（検証するには手動でFCPXMLを書き出して実際の記述を見る必要がある）。`<event uid="...">` で明示指定する手もあるが、ライブラリDB内に候補UUIDが2種類（`ZCOLLECTION.ZIDENTIFIER` と メタデータ内 `FFLibraryItem.identifier`）あり、どちらが対応するか未確認。

## 画像を素材として入れる（プロジェクトを作らない）

**`--assets-only` を使う。** これを付けないとタイムライン（プロジェクト）まで一緒に作られる。素材だけ入れたい場合に余計なプロジェクトが増える。

```bash
python3 build_fcpxml.py photos/本番 -o out/assets_only.fcpxml \
  --event "wedding-movie" --library ~/Movies/結婚式.fcpbundle \
  --assets-only --keyword "画像データ"
```

生成されたFCPXMLをダブルクリック（または `open -a` でアプリ指定）すると「XMLを読み込む」ダイアログが出る。**ユーザーが「読み込む」を押すまでライブラリには入らない。**

## フォルダにクリップは入れられない

Final Cutのフォルダは「クリップの入れ物」ではなく「コレクションの整理棚」。DTDの定義:

```
<!ELEMENT collection-folder (collection-folder | keyword-collection | smart-collection)*>
```

クリップをまとめたい場合は**キーワードコレクション**（サイドバーの鍵マーク）を使う。`--keyword` で各クリップに `<keyword value="..."/>` を付けると、Final Cut側が同名のキーワードコレクションを自動生成する。

入れ子にしたい場合は、できたキーワードコレクションをフォルダにドラッグする（`📁フォルダ > 🔑キーワードコレクション > クリップ`）。これは可能な操作。

## ブラウザの日付見出しはフォルダではない

イベント内に見える `2026/08/02` のような項目は、Final Cutがクリップを日付でグループ表示しているだけ。フォルダやコレクションではないので、これを作る・指定することはできない。

## 状態を確認する手順

### 早見（フォルダ構成）

`.fcpbundle` はパッケージなので `ls` で中を見られる。**直下のフォルダ＝イベント、その配下のフォルダ＝プロジェクト**。

```bash
ls ~/Movies/結婚式.fcpbundle/              # イベント一覧
ls ~/Movies/結婚式.fcpbundle/wedding-movie/  # 配下のプロジェクト
```

イベントとプロジェクトはどちらも `CurrentVersion.fcpevent` を持つため、ファイル構成では区別できない。階層で判断する。

### 中身の確認（SQLite）

カタログはSQLite。**Final Cut 起動中は直接触らず、コピーしてから読む**。

```bash
cp ~/Movies/結婚式.fcpbundle/wedding-movie/CurrentVersion.fcpevent /tmp/ev.sqlite
sqlite3 /tmp/ev.sqlite "select ZTYPE, count(*) from ZCOLLECTION where ZTYPE like 'FF%' group by ZTYPE order by 2 desc"
```

| ZTYPE | 意味 |
|---|---|
| `FFAssetRef` | **ブラウザ上のクリップ数**（これが素材の件数） |
| `FFAsset` / `FFMediaRep` | メディア実体の登録 |
| `FFAnchoredKeywordMarker` | クリップに付いたキーワード |
| `FFMediaEventKeyword` | キーワードコレクション |
| `FFMediaEventProject` | プロジェクト |
| `FFMediaEventFolder` | フォルダ（rootFolderを含むため常に1以上） |

ライブラリ側（`CurrentVersion.flexolibrary`）では `ZCOLLECTION.ZTYPE` が `FFEventRecord`＝イベント、`FFSequenceRecord`＝プロジェクト、`FFLibrary`＝ライブラリ自身。階層は `Z_3CHILDCOLLECTIONS`、表示名は `ZCOLLECTIONMD.ZDICTIONARYDATA`（NSKeyedArchiver形式のplist）の `relativePath`。

読めるのは**保存済みの状態のみ**。作成直後の確認は少し待つ。

## 注意

- **プロジェクトは取り込みのたびに新規作成される。** 同名なら「名前 1」が増える。既存プロジェクトへの追記はできない
- **同名の画像を再取り込みすると、ライブラリ内に `01 (fcp1).jpg` のような別名コピーが増える。** 参照されないファイルが残るので「未使用メディアを削除」で整理する
- **`__Trash` はFinal Cut内部のゴミ箱。** 空にすると復元できない。イベント・クリップの削除はここに入る
- メディアの持ち方は2通り。シンボリックリンク（読み込み時に「ファイルの場所に残す」）とライブラリ内コピー。`2026-07-26` はリンク、`wedding-movie` はコピーになっている。コピーなら元の写真を移動・削除してもリンクが切れない
- ライブラリ・`photos/` は `.gitignore` 対象。写真は顔が識別できる個人情報なのでコミットしない
