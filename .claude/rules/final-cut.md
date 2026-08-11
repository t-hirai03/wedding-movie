# Final Cut Pro ライブラリ規約

## ライブラリ

| 項目 | 値 |
|---|---|
| ライブラリ | `~/Movies/結婚式.fcpbundle` |
| Final Cut Pro | 12.3（FCPXMLは1.14まで対応。`build_fcpxml.py` は1.13を出力） |

## イベントとプロジェクトの使い分け

| イベント | 用途 |
|---|---|
| `本番ムービー` | **本番の制作はここ。** 実際に式で流すプロジェクトを配下に作る |
| `2026-07-26` | 検証用。`テスト` / `テスト_自動生成_v1` 等はFCPXML取り込みの動作確認プロジェクト |
| `素材` | 素材置き場（現在空） |

FCPXMLの取り込み検証は `2026-07-26` で行い、本番プロジェクトを検証で汚さない。

`build_fcpxml.py` の `--event` に本番イベントを指定すると本番側にプロジェクトが増えるため、検証時は `--event 2026-07-26` を明示する。

## 状態を確認する手順

### 早見（フォルダ構成）

`.fcpbundle` はパッケージなので `ls` で中を見られる。**直下のフォルダ＝イベント、その配下のフォルダ＝プロジェクト**。

```bash
ls ~/Movies/結婚式.fcpbundle/            # イベント一覧
ls ~/Movies/結婚式.fcpbundle/本番ムービー/  # 配下のプロジェクト
```

イベントとプロジェクトはどちらも `CurrentVersion.fcpevent` を持つため、ファイル構成では区別できない。階層で判断する。

### 厳密な確認（種別の判定）

ライブラリのカタログは SQLite。**Final Cut 起動中は直接触らず、コピーしてから読む**。

```bash
cp ~/Movies/結婚式.fcpbundle/CurrentVersion.flexolibrary /tmp/lib.sqlite
sqlite3 -header -column /tmp/lib.sqlite "select Z_PK, ZTYPE from ZCOLLECTION where ZTYPE like 'FF%'"
sqlite3 -header -column /tmp/lib.sqlite "select * from Z_3CHILDCOLLECTIONS"
```

| 見るもの | 意味 |
|---|---|
| `ZCOLLECTION.ZTYPE = FFEventRecord` | イベント |
| `ZCOLLECTION.ZTYPE = FFSequenceRecord` | プロジェクト |
| `ZCOLLECTION.ZTYPE = FFLibrary` | ライブラリ自身 |
| `Z_3CHILDCOLLECTIONS` | 親子関係（ライブラリ→イベント→プロジェクト） |

表示名は `ZCOLLECTION.ZNAME` ではなく `ZCOLLECTIONMD.ZDICTIONARYDATA`（NSKeyedArchiver形式のplist）の `relativePath` に入っている。Pythonの `plistlib` で `$objects[1]` の `NS.keys` / `NS.objects` を突き合わせて取り出す。

読めるのは**保存済みの状態のみ**。Final Cut が未保存の変更を持っている場合は反映されないので、作成直後の確認は少し待つ。

## 新規プロジェクトの作り方

⌘N（新規プロジェクト）と ⌥⌘N（新規イベント）を間違えやすい。プロジェクトを作るときは:

1. サイドバーで対象イベントを選択
2. ファイル → 新規 → プロジェクト（⌘N）

イベント配下にプロジェクトが現れなければ、イベントを作ってしまっている。

## 注意

- 同名プロジェクトにFCPXMLを再取り込みすると「名前 1」で複製が増える。不要な複製は削除する
- ライブラリ・`photos/` は `.gitignore` 対象。写真は顔が識別できる個人情報なのでコミットしない
