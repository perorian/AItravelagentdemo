import os
from openai import AzureOpenAI
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Azure OpenAIの設定
endpoint = "https://railo-mal0y2to-eastus2.openai.azure.com/"
deployment = "gpt-4.1-mini"
api_version = "2025-01-01-preview"

# 会話管理の設定
MAX_CONVERSATION_HISTORY = 10  # 保持する会話ターン数
SYSTEM_PROMPT = """あなたは旅行プランニングの専門家です。
ユーザーの予算、希望する場所、活動に基づいて非常に詳細な旅行プランを提案してください。
必ず完全な旅行プランを提供し、途中で終わらないようにしてください。
回答は必ず最後まで完結させてください。"""

# APIキーを環境変数から取得
subscription_key = os.environ.get("AZURE_OPENAI_API_KEY")
if not subscription_key:
    print("APIキーが設定されていません。.envファイルを確認してください。")
    exit(1)

print(f"API Key: {subscription_key[:10]}...")

# Azure OpenAI クライアントの初期化
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version=api_version,
)

def get_streaming_response(messages):
    """ストリーミングレスポンスを取得する関数"""
    try:
        print("\nアシスタント: ", end="")
        
        response = client.chat.completions.create(
            stream=True,
            messages=messages,
            max_tokens=10000,  # 出力トークン数の上限
            temperature=0.7,
            model=deployment,
        )
        
        # 応答テキストを集める
        full_response = ""
        for update in response:
            if update.choices:
                content = update.choices[0].delta.content or ""
                print(content, end="", flush=True)
                full_response += content
        
        print("\n" + "-" * 80)  # 区切り線を追加
        return full_response
    
    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")
        print(f"エラータイプ: {type(e).__name__}")
        return f"エラーが発生しました: {str(e)}"

def manage_conversation_history(messages):
    """会話履歴を管理し、トークン制限内に収める関数"""
    # システムメッセージは常に保持
    system_message = messages[0]
    
    # 会話履歴が長すぎる場合は古いメッセージを削除
    if len(messages) > (MAX_CONVERSATION_HISTORY * 2 + 1):  # システムメッセージ + ユーザー/アシスタントのペア
        # システムメッセージを保持し、直近のMAX_CONVERSATION_HISTORYペアのメッセージだけを残す
        messages = [system_message] + messages[-(MAX_CONVERSATION_HISTORY * 2):]
        print(f"\n[注意] 会話履歴が長くなったため、古いメッセージを削除しました。直近の{MAX_CONVERSATION_HISTORY}回の会話のみを保持しています。")
    
    return messages

def main():
    print("=" * 80)
    print("==== 旅行プランニングチャットを開始します ====")
    print("旅行の質問や要望を入力してください。終了するには「終了」と入力してください。")
    print("=" * 80)
    
    # 会話メッセージの初期化
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]
    
    # 会話ループ
    while True:
        # ユーザー入力を取得
        user_input = input("\nあなた: ")
        
        # 終了条件のチェック
        if user_input.lower() in ["終了", "exit", "quit"]:
            print("チャットを終了します。")
            break
        
        # ユーザー入力をメッセージ履歴に追加
        messages.append({"role": "user", "content": user_input})
        
        # 会話履歴を管理
        messages = manage_conversation_history(messages)
        
        # APIリクエスト送信中のメッセージ
        print("APIリクエスト送信中...")
        
        try:
            # ストリーミングレスポンスを取得
            ai_response = get_streaming_response(messages)
            
            # 応答をメッセージ履歴に追加
            messages.append({"role": "assistant", "content": ai_response})
        except Exception as e:
            print(f"\nエラーが発生しました: {str(e)}")
            # エラーが発生した場合、最後のユーザーメッセージを履歴から削除
            if len(messages) > 0 and messages[-1]["role"] == "user":
                messages.pop()
    
    # クライアントを閉じる
    client.close()

if __name__ == "__main__":
    main()
