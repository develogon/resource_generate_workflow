"""
コンテンツジェネレータのテスト用サンプルデータ
"""

# セクション構造サンプルデータ（YAML形式）
SAMPLE_STRUCTURE_YAML = """
title: "テストタイトル"
chapters:
  - id: "01"
    title: "第1章 はじめに"
    sections:
      - id: "01"
        title: "配列"
        learning_objectives:
          - "Goの配列の基本的な宣言方法を理解する"
          - "配列リテラルと要素アクセスの方法を習得する"
        paragraphs:
          - type: "introduction_with_foreshadowing"
            order: 1
            content_focus: "配列の存在と使用頻度の少なさへの言及"
            original_text: "Go言語にも配列 (array)がありますが、配列が直接使われることは多くはありません。"
            content_sequence:
              - type: "explanation"
                order: 1
                config:
                  style: "introduction"
                  key_points:
                    - "配列の存在確認"
                    - "使用頻度の低さ"
"""

# サンプルテンプレート
SAMPLE_TEMPLATE = """
# {{title}}

## 概要

{{summary}}

## 詳細

言語: {{language}}
難易度: {{difficulty}}

{{content}}
"""

# サンプルコンテキスト
SAMPLE_CONTEXT = {
    "title": "サンプルタイトル",
    "summary": "これはサンプル概要です。",
    "language": "Go",
    "difficulty": "中級",
    "content": "ここに本文が入ります。"
}

# サンプル生成コンテンツ
SAMPLE_GENERATED_CONTENT = """
# サンプルタイトル

## 概要

これはサンプル概要です。

## 詳細

言語: Go
難易度: 中級

ここに本文が入ります。
""" 