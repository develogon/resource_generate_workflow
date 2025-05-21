# セクション構造生成プロンプト

## 指示

あなたは教育コンテンツ構造化のエキスパートです。以下のセクション内容を分析し、効果的な学習構造を持つYAML形式の構造定義を作成してください。

## 入力

### セクションタイトル
{{section_title}}

### 章タイトル
{{chapter_title}}

### セクション内容
```
{{content}}
```

## 出力形式

以下の形式でYAMLを出力してください。

```yaml
title: "{{chapter_title}}"
chapters:
  - id: "{{chapter_id}}"
    title: "{{chapter_title}}"
    sections:
      - id: "{{section_id}}"
        title: "{{section_title}}"
        
        # セクション情報
        learning_objectives:
          - "目標1"
          - "目標2"
          - "目標3"
        
        # パラグラフ定義
        paragraphs:
          - type: "introduction"  # パラグラフの種類を表す識別子
            order: 1  # 順序
            content_focus: "導入部分の要点"
            original_text: |
              # 元のテキスト内容
            
            content_sequence:
              - type: "explanation"  # コンテンツ要素のタイプ
                order: 1  # 順序
                config:
                  style: "introduction"
                  key_points:
                    - "ポイント1"
                    - "ポイント2"
                  preserve_elements:
                    - "保持すべき表現や特徴"
              
              - type: "image"  # 必要に応じて画像要素を含める
                order: 2
                config:
                  type: "concept_overview"
                  description: "画像の説明"
                  slide_structure:
                    - "スライド構造要素1"
                    - "スライド構造要素2"
```

## 具体的なガイドライン

1. **学習目標**:
   - セクションから読み取れる主要な学習目標を3〜5つ抽出してください
   - 目標は「〜を理解する」「〜を習得する」などの形式で記述してください

2. **パラグラフ分割**:
   - セクション内容を論理的なパラグラフに分割してください
   - 各パラグラフには適切な識別子をつけてください（例: introduction, concept_explanation, code_example, summary）
   - 元のテキストをそのまま保持してください

3. **コンテンツシーケンス**:
   - 各パラグラフをさらに細かいコンテンツ要素に分解してください
   - 要素のタイプには explanation, code, image, list, example などがあります
   - 各要素に必要な設定情報を config セクションに含めてください

4. **保持要素**:
   - 元のテキストの特徴的な表現や教授スタイルを preserve_elements に記録してください
   - これには特有の言い回しや、技術的用語の説明方法などが含まれます

## 重要事項

- 入力内容を正確に分析し、教育効果の高い構造設計を行ってください
- コード例や技術的な概念については特に注意深く分析してください
- 最終的なYAMLはコンテンツ生成システムによって処理されるため、正確な構造を維持してください 