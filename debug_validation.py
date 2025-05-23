from src.utils.validation import validate_markdown_content, validate_file_path, validate_content_structure

# リンクテスト
content = """# リンクテスト

[正常なリンク](https://example.com)
[空のURL]()
[](https://example.com)
"""
result = validate_markdown_content(content)
print('リンクテスト:')
print('Valid:', result['valid'])
print('Errors:', result['errors'])
print('Warnings:', result['warnings'])
print('Link count:', result['stats']['link_count'])
print()

# 空のパステスト
result2 = validate_file_path("")
print('空のパステスト:')
print('Valid:', result2['valid'])
print('Errors:', result2['errors'])
print('Warnings:', result2['warnings'])
print()

# 画像テスト
content3 = """# 画像テスト

![正常な画像](image.png)
![](empty-alt.png)
![alt text]()
"""
result3 = validate_markdown_content(content3)
print('画像テスト:')
print('Valid:', result3['valid'])
print('Errors:', result3['errors'])
print('Warnings:', result3['warnings'])
print('Image count:', result3['stats']['image_count'])
print()

# 長いタイトルテスト
content4 = {
    "id": "test",
    "title": "非常に長いタイトル" * 20,
    "content": "コンテンツ" * 20
}
result4 = validate_content_structure(content4)
print('長いタイトルテスト:')
print('Valid:', result4['valid'])
print('Errors:', result4['errors'])
print('Warnings:', result4['warnings'])
print('Title length:', len(content4['title'])) 