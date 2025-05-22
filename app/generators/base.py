class BaseGenerator:
    """ジェネレータの基底クラス

    AIを活用したコンテンツ生成の基底クラスです。
    各種ジェネレータはこのクラスを継承して実装します。
    """

    def prepare_prompt(self, structure, additional_context=None):
        """プロンプトを準備する

        Args:
            structure (dict): 構造情報
            additional_context (dict, optional): 追加コンテキスト情報. デフォルトはNone

        Returns:
            str: 準備されたプロンプト
        """
        raise NotImplementedError("サブクラスで実装する必要があります")

    def process_response(self, response):
        """API応答を処理する

        Args:
            response (dict): API応答

        Returns:
            Any: 処理された応答
        """
        raise NotImplementedError("サブクラスで実装する必要があります")

    async def generate(self, input_data):
        """コンテンツを生成する

        Args:
            input_data (dict): 入力データ

        Returns:
            Any: 生成されたコンテンツ
        """
        raise NotImplementedError("サブクラスで実装する必要があります") 