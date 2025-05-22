## 指示
以下の内容をCodeVideoのアクションJSONに変換してください。

## 元の台本

```markdown
{{ARTICLE_CONTENT}}
```

## 重要な指示

JSONでは以下のアクションのみを使用できます：
- author-speak-before（説明話法）
- editor-type（エディタ入力）
- editor-save（保存、value="1"で保存）
- editor-arrow-up/down/left/right（カーソル移動）
- editor-enter（改行、valueの数だけ改行される）
- editor-backspace（削除）
- editor-space（スペース、valueの数だけスペースが挿入される）
- file-explorer-create-file（ファイル作成）
- file-explorer-open-file（ファイル開く）
- file-explorer-create-folder（フォルダ作成）
- mouse-click-filename（ファイル領域クリック）
- mouse-click-editor（エディタ領域クリック）
- slide-viewer（画像スライド表示）
```

## CodeVideoスクリプト作成のベストプラクティス

作成されるJSONスクリプトが高品質になるよう、以下のベストプラクティスを参考にしてください：

1. **基本構造を守る**
   - 必ず定義されているアクションのみを使用する
   - 各アクションは `{ "name": "アクション名", "value": "値" }` の形式で記述

2. **アクションの正確な使用法**
   - `editor-enter`：value="1"で1回改行、value="2"で2回改行（数値=改行回数）
   - `editor-space`：value="4"で4つのスペースを挿入（数値=スペース数）
   - `editor-save`：常にvalue="1"で使用

3. **ファイル操作のフロー**
   - フォルダ作成 → ファイル作成 → ファイルを開く の順序を守る
   - ファイル・フォルダパスは正確に（例：`src/components/Button.js`）

4. **コーディング時の注意点**
   - `editor-type`でコード入力後は必ず`editor-save`を行う
   - 複雑なコードは小さな単位で入力し、その都度説明を入れる
   - インデントは`editor-space`で適切な数を指定する

5. **説明のベストプラクティス**
   - 重要な概念の前には`author-speak-before`で説明を入れる
   - 簡潔で分かりやすい説明を心がける
   - コードの動作説明は実際のコードと一致させる

6. **リンターエラー防止**
   - 適切な構文を使用し、セミコロンやカッコの閉じ忘れに注意
   - 言語固有の規則に従ったコーディングスタイルを使用

## 具体例：Pythonの基本出力プログラム

以下は、簡単なPythonプログラムを作成するCodeVideo JSONの例です：

```json
[
  {
    "name": "author-speak-before",
    "value": "Pythonでの基本的な出力方法について学びましょう"
  },
  {
    "name": "file-explorer-create-file",
    "value": "hello.py"
  },
  {
    "name": "file-explorer-open-file",
    "value": "hello.py"
  },
  {
    "name": "author-speak-before",
    "value": "まずは基本的なprint文を書いてみましょう"
  },
  {
    "name": "editor-type",
    "value": "print('Hello, World!')"
  },
  {
    "name": "editor-save",
    "value": "1"
  },
  {
    "name": "author-speak-before",
    "value": "次に、変数を使った出力をしてみましょう"
  },
  {
    "name": "editor-enter",
    "value": "2"
  },
  {
    "name": "editor-type",
    "value": "name = \"Python学習者\""
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-type",
    "value": "print('こんにちは、' + name + 'さん！')"
  },
  {
    "name": "editor-save",
    "value": "1"
  },
  {
    "name": "author-speak-before",
    "value": "Pythonでは、f文字列を使うと変数を簡単に文字列に埋め込めます"
  },
  {
    "name": "editor-enter",
    "value": "2"
  },
  {
    "name": "editor-type",
    "value": "age = 25"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-type",
    "value": "print(f'{name}さんは{age}歳です')"
  },
  {
    "name": "editor-save",
    "value": "1"
  },
  {
    "name": "author-speak-before",
    "value": "これで基本的な出力方法を学びました。実行するとこのように出力されます。"
  }
]
```

## 注意点

- 関数終了後の閉じ括弧を忘れない
- インデントはスペース4つが標準 (`editor-space` で値 "4" を使用)
- タグの閉じ忘れに注意
- CSSセレクタと波括弧の構文を正確に

## 応用：フォルダ構造を持つプロジェクト例

複数のファイルやフォルダを含むプロジェクトの場合は、以下のように構造化します：

```json
[
  {
    "name": "author-speak-before",
    "value": "簡単なWebアプリのフォルダ構造を作成していきます"
  },
  {
    "name": "file-explorer-create-folder",
    "value": "src"
  },
  {
    "name": "file-explorer-create-folder",
    "value": "src/components"
  },
  {
    "name": "file-explorer-create-file",
    "value": "src/index.js"
  },
  {
    "name": "file-explorer-open-file",
    "value": "src/index.js"
  },
  {
    "name": "editor-type",
    "value": "import { App } from './components/App';"
  },
  {
    "name": "editor-enter",
    "value": "2"
  },
  {
    "name": "editor-type",
    "value": "document.getElementById('root').appendChild(App());"
  },
  {
    "name": "editor-save",
    "value": "1"
  },
  {
    "name": "file-explorer-create-file",
    "value": "src/components/App.js"
  },
  {
    "name": "file-explorer-open-file",
    "value": "src/components/App.js"
  },
  {
    "name": "editor-type",
    "value": "export function App() {"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "2"
  },
  {
    "name": "editor-type",
    "value": "const app = document.createElement('div');"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "2"
  },
  {
    "name": "editor-type",
    "value": "app.textContent = 'Hello CodeVideo!';"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "2"
  },
  {
    "name": "editor-type",
    "value": "return app;"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-type",
    "value": "}"
  },
  {
    "name": "editor-save",
    "value": "1"
  }
]
```

## カーソル移動と編集の例

コードを修正する場合のカーソル移動と編集の例です：

```json
[
  {
    "name": "author-speak-before",
    "value": "既存のコードを修正してみましょう"
  },
  {
    "name": "editor-arrow-up",
    "value": "3"
  },
  {
    "name": "editor-arrow-right",
    "value": "10"
  },
  {
    "name": "editor-backspace",
    "value": "5"
  },
  {
    "name": "editor-type",
    "value": "新しい値"
  },
  {
    "name": "editor-save",
    "value": "1"
  },
  {
    "name": "author-speak-before",
    "value": "これで修正が完了しました"
  }
]
```

以上のガイドラインを参考に、効果的なCodeVideoスクリプトを作成してください。定義されているアクションのみを使用し、コーディングの流れを自然に表現することで、質の高い教育コンテンツが作成できます。