## はじめに

この記事はAPIの基本的な実装方法を丁寧に解説します。基礎を学びたい方、今更聞けないような知識の振り返りを求める方の役に立つことを願っています。

:::note
[こちら](https://www.recruit.nuco.co.jp/?qiita_item_id=7dab01ac2ea08b85fb15)まで。
:::

### HTTP

HTTPとは、WebサーバとWebクライアントの間でデータの送受信を行うために用いられるプロトコル（通信方法）です。

https://qiita.com/Sekky0905/items/dff3d0da059d6f5bfabf

> **HTTPS**：
> - HTTPにセキュリティ機能（Secure）を追加したプロトコル
> - 通信内容の暗号化を行い、中間者の攻撃やデータの傍受を防ぐ
> - URLが「https://」で始まるウェブサイトは、このHTTPSプロトコルを使用しており、ブラウザのアドレスバーには鍵のアイコンや「安全」と表示がされることが多い

![alt text](https://learning.oreilly.com/api/v2/epubs/urn%3Aorm%3Abook%3A9784873119786/files/images/pr2e_0301.png)

### 基本構造

```bash
pip install Flask
```

まず、main.pyを作成していきます。現時点のディレクトリ構造は以下のようになります。

```
.
├── app/
│   └── main.py
└── requirements.txt
```

```python:main.py
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "こんにちは！"

if __name__ == '__main__':
    app.run(debug=True)
```

- デコレータ`@app.route("/")`は、URLのルート（例: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)）へのアクセスがあった場合に、次に定義される関数（この場合はhello()）を呼び出すようにFlaskに指示しています。


![image.png](https://qiita-image-store.s3.ap-northeast-1.amazonaws.com/0/3025452/92dc8ec2-3b3c-3469-647d-83d857951b04.png)

また**curlコマンド**を使うことで、簡単にHTTPプロトコルでのデータ送受信を行うことができます。
