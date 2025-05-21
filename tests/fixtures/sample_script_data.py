"""
スクリプトおよびスクリプトJSON生成のテスト用サンプルデータ
"""

# スクリプト用サンプル入力データ
SAMPLE_SCRIPT_INPUT = {
    "section_title": "Goの並行処理",
    "content": "Goの並行処理機能についての解説です。goroutineとchannelを使った例を紹介します。",
    "template_path": "templates/script.md",
    "language": "Go"
}

# スクリプト用サンプルテンプレート
SAMPLE_SCRIPT_TEMPLATE = """
# {{section_title}} スクリプト

## ナレーション

今回は{{language}}の{{section_title}}について解説します。

## 内容

{{content}}

## 補足事項

コード例も紹介しながら解説します。
"""

# サンプル生成スクリプト
SAMPLE_GENERATED_SCRIPT = """
# Goの並行処理 スクリプト

## ナレーション

今回はGoの並行処理について解説します。

## 内容

Goの並行処理機能についての解説です。goroutineとchannelを使った例を紹介します。

## スクリプト

ナレーター: 「Goの並行処理の特徴は、軽量なgoroutineとchannelによる通信にあります。」

(コード例表示)

ナレーター: 「上記のようにgo キーワードでgoroutineを簡単に起動できます。」
"""

# JSONスクリプト用サンプル入力データ
SAMPLE_JSON_SCRIPT_INPUT = {
    "ARTICLE_CONTENT": """# Goの並行処理

## 概要
Goの並行処理機能は、goroutineとchannelを使って実装されています。
goroutineは軽量なスレッドのようなもので、非常に少ないリソースで実行できます。

## サンプルコード
```go
package main

import (
    "fmt"
    "time"
)

func main() {
    // goroutineの起動
    go func() {
        fmt.Println("goroutineで実行")
    }()
    
    // channelの作成と使用
    ch := make(chan string)
    go func() {
        ch <- "Hello from goroutine"
    }()
    
    msg := <-ch
    fmt.Println(msg)
    
    time.Sleep(time.Second)
}
```

これでgoroutineとchannelの基本が理解できます。
""",
    "template_path": "templates/prompts/script_json.md"
}

# サンプル生成JSONスクリプト
SAMPLE_GENERATED_JSON_SCRIPT = """
[
  {
    "name": "author-speak-before",
    "value": "Goの並行処理について解説します。goroutineとchannelという概念が重要です。"
  },
  {
    "name": "file-explorer-create-file",
    "value": "main.go"
  },
  {
    "name": "file-explorer-open-file",
    "value": "main.go"
  },
  {
    "name": "author-speak-before",
    "value": "まずはパッケージ宣言と必要なインポートから始めましょう"
  },
  {
    "name": "editor-type",
    "value": "package main"
  },
  {
    "name": "editor-enter",
    "value": "2"
  },
  {
    "name": "editor-type",
    "value": "import ("
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "\"fmt\""
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "\"time\""
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-type",
    "value": ")"
  },
  {
    "name": "editor-enter",
    "value": "2"
  },
  {
    "name": "author-speak-before",
    "value": "次にmain関数を定義し、goroutineを起動します"
  },
  {
    "name": "editor-type",
    "value": "func main() {"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "// goroutineの起動"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "go func() {"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "8"
  },
  {
    "name": "editor-type",
    "value": "fmt.Println(\"goroutineで実行\")"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "}()"
  },
  {
    "name": "editor-enter",
    "value": "2"
  },
  {
    "name": "author-speak-before",
    "value": "次にchannelを使った通信を実装します"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "// channelの作成と使用"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "ch := make(chan string)"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "go func() {"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "8"
  },
  {
    "name": "editor-type",
    "value": "ch <- \"Hello from goroutine\""
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "}()"
  },
  {
    "name": "editor-enter",
    "value": "2"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "msg := <-ch"
  },
  {
    "name": "editor-enter",
    "value": "1"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "fmt.Println(msg)"
  },
  {
    "name": "editor-enter",
    "value": "2"
  },
  {
    "name": "author-speak-before",
    "value": "最後に少し待機して、goroutineが完了する時間を確保します"
  },
  {
    "name": "editor-space",
    "value": "4"
  },
  {
    "name": "editor-type",
    "value": "time.Sleep(time.Second)"
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
  },
  {
    "name": "author-speak-before",
    "value": "このように、Goでは簡単に並行処理を実装できます。goroutineは軽量で、channelを使って安全に通信できます。"
  }
]
""" 