import autogen
from autogen.agentchat.contrib.text_analyzer_agent import TextAnalyzerAgent
from autogen.agentchat.contrib.group_chat_manager import GroupChatManager
from autogen.agentchat.conditions import TextMentionTermination
from autogen.agentchat.teams import RoundRobinGroupChat
from autogen.agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os
import getpass
import streamlit as st

from dotenv import load_dotenv
from autogen_core.tools import FunctionTool
from yahooquery import Ticker

# 環境変数の読み込み
load_dotenv()

# Azure OpenAIの設定
AZURE_OPENAI_ENDPOINT = "https:/m"
AZURE_OPENAI_DEPLOYMENT = "gpt-4.1-mini"
AZURE_OPENAI_API_VERSION = "2025-01-01-preview"

# APIキーを環境変数から取得
api_key = os.environ.get("AZURE_OPENAI_API_KEY")
if not api_key:
    raise ValueError("AZURE_OPENAI_API_KEYが設定されていません。.envファイルを確認してください。")

# 為替レート取得関数の定義
def get_exchange_rate(currency_code: str) -> dict:
    """
    指定した国の通貨と日本円（JPY）の為替レートを取得する。

    Args:
        currency_code (str): 通貨コード（例: "USD", "EUR", "GBP"）

    Returns:
        dict: 為替レート情報（通貨ペア、レート、取得時間）
    """
    symbol = f"{currency_code}JPY=X"  # 例: "USDJPY=X"
    ticker = Ticker(symbol)
    data = ticker.price[symbol]

    if "regularMarketPrice" in data:
        return {
            "currency_pair": f"{currency_code}/JPY",
            "exchange_rate": data["regularMarketPrice"],
            "timestamp": data["regularMarketTime"]
        }

    return {"error": "為替レートが取得できませんでした"}

# Function Callingの定義
get_exchange_rate_tool = FunctionTool(
    get_exchange_rate,
    description="現在の為替レートを取得します。"
)

# Azure OpenAIモデルクライアントの作成
model_client = OpenAIChatCompletionClient(
    model=AZURE_OPENAI_DEPLOYMENT,
    api_key=api_key,
    base_url=f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}",
    api_type="azure",
    api_version=AZURE_OPENAI_API_VERSION
)

# エージェントの定義
planner_agent = autogen.AssistantAgent(
    "planner_agent",
    model_client=model_client,
    description="An assistant that helps plan your trip.",
    system_message="You are a helpful assistant who proposes travel plans based on the user's requests."
)

local_agent = autogen.AssistantAgent(
    "local_agent",
    model_client=model_client,
    description="An assistant who suggests local activities and places to visit.",
    system_message="You are a helpful assistant who suggests authentic and interesting local activities and places to visit, utilizing the provided context information."
)

language_agent = autogen.AssistantAgent(
    "language_agent",
    model_client=model_client,
    description="An assistant who provides language tips for specific destinations.",
    system_message="You are a helpful assistant who gives important tips on language and communication challenges at specific destinations."
)

exchange_agent = autogen.AssistantAgent(
    name="exchange_agent",
    model_client=model_client,
    description="An assistant who provides information about currencies at travel destinations.",
    system_message="You are a helpful assistant who can provide exchange rates between the local currency and Japanese Yen at travel destinations using the get_exchange_rate_tool.",
    tools=[get_exchange_rate_tool]
)

travel_summary_agent = autogen.AssistantAgent(
    "travel_summary_agent",
    model_client=model_client,
    description="An assistant who summarizes the travel plan.",
    system_message="""You are a helpful assistant who integrates all suggestions and advice from other agents and provides a detailed final travel plan.
    Make sure the final plan is integrated and complete.
    The final response must be a complete plan."""
)

# ユーザープロキシエージェントの定義
user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    input_func=input
)

# 会話終了の条件を定義（APPROVEで終了）
termination = TextMentionTermination("APPROVE")

# グループチャットの定義
group_chat = RoundRobinGroupChat(
    [user_proxy, planner_agent, local_agent, language_agent, exchange_agent, travel_summary_agent],
    termination_condition=termination,
    max_turns=10
)

def main():
    # UIの作成
    ui = Console(group_chat)

    # チャット開始（英語の初期メッセージ）
    ui.run(
        """Hello! I would like to discuss my travel plans.
        My budget is 300,000 yen and I want to plan a 5-day trip to Europe.
        I would like to visit Paris, Rome, and Barcelona.
        I enjoy visiting museums and gourmet food."""
    )

    # 仮のエージェントリスト
    agents = ["planner_agent", "exchange_agent", "local_agent", "summary_agent"]

    # 会話履歴の仮データ
    conversation_history = [
        {"name": "planner_agent", "content": "どこに行きたいですか？"},
        {"name": "user", "content": "日本に行きたいです。"},
        {"name": "exchange_agent", "content": "現在の為替レートは..."},
    ]

    # 現在のスピーカー（例）
    current_speaker = "exchange_agent"

    st.title("Travel Planning Agent Visualization")
    st.write("Watch how different agents collaborate to create your travel plan!")

    initial_message = st.text_area("Describe your travel plans:")

    if st.button("Generate Travel Plan"):
        status_placeholder = st.empty()  # スピーカー表示用の空コンテナ
        conversation_placeholder = st.empty()  # 会話履歴表示用

        # 会話履歴を保存
        conversation_history = []

        # 会話を開始
        user_proxy.initiate_chat(
            group_chat,
            message=initial_message
        )

        # 各メッセージごとに表示を更新
        for message in group_chat.messages:
            current_speaker = message.get("name", "Unknown")
            status_placeholder.info(f"🗣️ Now speaking: **{current_speaker}**")
            conversation_history.append(f"**[{current_speaker}]**: {message['content']}")
            conversation_placeholder.markdown("\n".join(conversation_history))

if __name__ == "__main__":
    main() 
