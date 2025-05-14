import streamlit as st
import autogen
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from yahooquery import Ticker
import atexit
import time

# 環境変数の読み込み
load_dotenv()

# Azure OpenAIの設定
endpoint = "https://ai-railokanamura6054ai357603302162.openai.azure.com"
deployment = "gpt-4.1-nano"
subscription_key = "1hBfgjzrczxeW4vA0y8kofJiVKyRpreIwOTm6VqD3W1RBMHdggSDJQQJ99BEACHYHv6XJ3w3AAAAACOGr3Dc"
api_version = "2025-01-01-preview"

# Azure OpenAI クライアントの初期化
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version=api_version,
)

# APIキーを環境変数から取得
api_key = os.environ.get("AZURE_OPENAI_API_KEY")
if not api_key:
    st.error("AZURE_OPENAI_API_KEYが設定されていません。.envファイルを確認してください。")
    st.stop()

# 為替レート取得関数の定義
def get_exchange_rate(currency_code: str) -> dict:
    symbol = f"{currency_code}JPY=X"
    ticker = Ticker(symbol)
    data = ticker.price[symbol]
    
    if "regularMarketPrice" in data:
        return {
            "currency_pair": f"{currency_code}/JPY",
            "exchange_rate": data["regularMarketPrice"],
            "timestamp": data["regularMarketTime"]
        }
    return {"error": "為替レートが取得できませんでした"}

# エージェントの設定
config_list = [{
    "model": deployment,
    "api_key": subscription_key,
    "base_url": f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}",
    "api_type": "azure",
    "api_version": api_version
}]

# エージェントの定義
planner_agent = autogen.AssistantAgent(
    name="planner_agent",
    llm_config={"config_list": config_list},
    system_message="You are a helpful assistant who proposes travel plans based on the user's requests."
)

local_agent = autogen.AssistantAgent(
    name="local_agent",
    llm_config={"config_list": config_list},
    system_message="You are a helpful assistant who suggests authentic and interesting local activities and places to visit."
)

language_agent = autogen.AssistantAgent(
    name="language_agent",
    llm_config={"config_list": config_list},
    system_message="You are a helpful assistant who gives important tips on language and communication challenges."
)

exchange_agent = autogen.AssistantAgent(
    name="exchange_agent",
    llm_config={"config_list": config_list},
    system_message="You are a helpful assistant who can provide exchange rates and currency information."
)

travel_summary_agent = autogen.AssistantAgent(
    name="travel_summary_agent",
    llm_config={"config_list": config_list},
    system_message="""You are a helpful assistant who integrates all suggestions and provides a detailed final travel plan.
    Make sure the final plan is integrated and complete."""
)

# ユーザープロキシエージェントの定義
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config={"use_docker": False}
)

# グローバル変数
conversation_container = None

# エージェントのリスト
agents = [user_proxy, planner_agent, local_agent, language_agent, exchange_agent, travel_summary_agent]

# グループチャットの設定
groupchat = autogen.GroupChat(
    agents=agents,
    messages=[],
    max_round=10,
    speaker_selection_method="round_robin"  # エージェントの順番を制御
)

# グループチャットマネージャーの設定
manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config={
        "config_list": config_list,
        "temperature": 1,
        "top_p": 1,
        "max_tokens": 14315
    }
)

# Set up direct OpenAI streaming
def get_openai_streaming_response(prompt, system_message="You are a helpful travel assistant."):
    try:
        # Use the existing Azure OpenAI client
        response = client.chat.completions.create(
            stream=True,
            messages=[
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=800,
            temperature=0.7,
            top_p=1.0,
            model=deployment,
        )
        
        return response
    except Exception as e:
        st.error(f"Error connecting to OpenAI API: {str(e)}")
        return None

# Enhanced streaming message display function
def display_streaming_message(message, role_display, bg_color, use_api_streaming=False):
    placeholder = st.empty()
    
    # Initial display
    placeholder.markdown(f"<div style='background-color:{bg_color}; padding:10px; border-radius:5px; margin-bottom:10px;'><b>{role_display}:</b> <span id='typing-text'></span></div>", unsafe_allow_html=True)
    
    if use_api_streaming:
        # Get system message based on agent role
        system_message = f"You are a {role_display} helping travelers plan their trips."
        
        # Create a prompt based on the conversation context
        prompt = f"Respond as a {role_display} about the following travel plan: {message}"
        
        # Get the streaming response
        response = get_openai_streaming_response(prompt, system_message)
        
        if response:
            full_message = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_message += content
                    placeholder.markdown(f"<div style='background-color:{bg_color}; padding:10px; border-radius:5px; margin-bottom:10px;'><b>{role_display}:</b> {full_message}</div>", unsafe_allow_html=True)
                    time.sleep(0.01)  # Small delay for smooth streaming
    else:
        # Fallback to word-by-word display if not using API streaming
        full_message = ""
        words = message.split()
        for i, word in enumerate(words):
            full_message += word + " "
            # Update the message every few words for a natural typing effect
            if i % 3 == 0 or i == len(words) - 1:
                placeholder.markdown(f"<div style='background-color:{bg_color}; padding:10px; border-radius:5px; margin-bottom:10px;'><b>{role_display}:</b> {full_message}</div>", unsafe_allow_html=True)
                time.sleep(0.1)  # Adjust speed here
    
    # Ensure the last part is displayed
    placeholder.markdown(f"<div style='background-color:{bg_color}; padding:10px; border-radius:5px; margin-bottom:10px;'><b>{role_display}:</b> {message}</div>", unsafe_allow_html=True)

# カスタムの会話表示関数
def display_conversation(message, role):
    global conversation_container
    with conversation_container:
        if role == "user_proxy":
            role_display = "User"
            st.markdown(f"<div style='background-color:#E6F7FF; padding:10px; border-radius:5px; margin-bottom:10px;'><b>{role_display}:</b> {message}</div>", unsafe_allow_html=True)
        elif role == "planner_agent":
            role_display = "Travel Planner"
            display_streaming_message(message, role_display, bg_color="#F0F8EA")
        elif role == "local_agent":
            role_display = "Local Guide"
            display_streaming_message(message, role_display, bg_color="#FFF8E1")
        elif role == "language_agent":
            role_display = "Language Assistant"
            display_streaming_message(message, role_display, bg_color="#F3E5F5")
        elif role == "exchange_agent":
            role_display = "Currency Advisor"
            display_streaming_message(message, role_display, bg_color="#E0F7FA", use_api_streaming=True)
        elif role == "travel_summary_agent":
            role_display = "Travel Summary"
            display_streaming_message(message, role_display, bg_color="#FFEBEE", use_api_streaming=True)
        else:
            st.markdown(f"<div style='background-color:#F5F5F5; padding:10px; border-radius:5px; margin-bottom:10px;'><b>{role}:</b> {message}</div>", unsafe_allow_html=True)
        
        # 自動スクロールのためのJavaScript
        st.markdown("""
        <script>
            var chatContainer = document.querySelector('.stMarkdown');
            if (chatContainer) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        </script>
        """, unsafe_allow_html=True)
        
        # 少し遅延を入れて会話が段階的に表示されるようにする
        time.sleep(0.5)

# Add a custom demo function for the app to show a conversation thread
def show_demo_conversation():
    global conversation_container
    with conversation_container:
        st.empty()  # Clear any existing content
        
        # User message
        user_message = """singapore at 5days

[Profile Information] Age: 30, Travel Style: Cultural Experience, Food, Budget: Standard"""
        display_conversation(user_message, "user_proxy")
        time.sleep(1)
        
        # Travel Planner response
        planner_message = """Hello! Here's a 5-day cultural and food-focused itinerary for Singapore that balances iconic sights, local flavors, and authentic experiences, all within a budget-friendly approach.

---

### Day 1: Arrival & Chinatown Exploration
**Morning:**
- Arrive in Singapore and check into your accommodation.
- Head to Chinatown, a bustling district filled with heritage and tasty eats.

**Afternoon:**
- Visit Chinatown Heritage Centre to learn about early Chinese immigrants.
- Explore Sri Mariamman Temple, Singapore's oldest Hindu temple.
- Sample affordable dishes at Chinatown Food Street or Maxwell Food Centre (try Hainanese Chicken Rice, Laksa).

**Evening:**
- Walk around Chinatown's lit-up streets and shops.
- Optional: Enjoy a drink at a rooftop bar like 1-Altitude for a view but budget-friendly options are available nearby.

---

### Day 2: Marina Bay & Civic District
**Morning:**
- Visit the Marina Bay Sands SkyPark for panoramic city views (free outdoor viewing area if you skip the SkyPark ticket).
- Walk around Gardens by the Bay, see the Supertree Grove, and explore Cloud Forest & Flower Dome (consider visiting at sunset or in the evening for cooler weather).

**Afternoon:**
- Explore the ArtScience Museum or the Esplanade Theatre.
- Walk past the historic Civic District: National Gallery Singapore and MERLION.

**Evening:**
- Watch the Marina Bay Sands light and water show (free).
- Dine at nearby affordable hawker centers like Lau Pa Sat or Satay by the Bay.

---

### Day 3: Little India & Kampong Glam
**Morning:**
- Head to Little India; visit Sri Veeramakaliamman Temple.
- Explore vibrant streets, markets, and street art.

**Afternoon:**
- Visit Kampong Glam, check out Sultan Mosque.
- Browse Haji Lane for boutique shops and street art.

**Evening:**
- Eat at local stalls and eateries – try Nasi Lemak, Satay, or Middle Eastern dishes in Kampong Glam.
- Optional: Attend a cultural performance at the Malay Heritage Centre.

---

### Day 4: Sentosa & Southern Islands
**Morning:**
- Take the free Sentosa Transit, or walk via the Sentosa Boardwalk.
- Explore Sentosa's beaches and Fort Siloso (free entry).

**Afternoon:**
- For budget-friendly activities, visit the Madame Tussauds or Aquarium only if interested; otherwise, enjoy the beaches and nature trails.

**Evening:**
- Return to the city; dine at a hawker center in VivoCity or nearby.

---

### Day 5: Local Markets & Departure
**Morning:**
- Visit Tiong Bahru Market & Food Centre for breakfast.
- Walk around Tiong Bahru neighborhood, known for art deco architecture and trendy cafes.

**Afternoon:**
- Last-minute shopping at Bugis Street Market or explore Orchard Road (if time permits).

**Evening:**
- Head to the airport for departure.

---

### Tips:
- Use public transport (MRT and buses) for affordable and efficient travel.
- Purchase an EZ-Link card for convenience and discounts.
- Check out free or low-cost attractions.
- Stick to hawker centers for authentic and budget-friendly meals.

Enjoy your cultural and flavorful journey in Singapore! If you'd like specific restaurant recommendations or personalized adjustments, just let me know."""
        display_conversation(planner_message, "planner_agent")
        time.sleep(1)
        
        # Local Guide response
        local_message = """Hello! Your 5-day Singapore itinerary is well-rounded and packed with cultural, culinary, and iconic sights. Here are some additional tips to make your trip even more memorable and budget-friendly:

**Transportation:**
- Get an EZ-Link card or Singapore Tourist Pass for unlimited rides on MRT and buses.
- Walk whenever possible—many neighborhoods are walkable and full of hidden gems.

**Dining:**
- Hawker centers are the best for authentic, budget-friendly local food.
- Food courts like Maxwell Food Centre, Lau Pa Sat, and Tiong Bahru Market are excellent choices.

**Cultural Tips:**
- Respect local customs, especially at religious sites like temples and mosques.
- Try local specialties: Hainanese Chicken Rice, Laksa, Satay, Nasi Lemak, and Kaya Toast.

**Additional Recommendations:**
- For free green spaces, visit MacRitchie Reservoir or Fort Canning Park.
- Check if there are any local festivals or events happening during your stay for an authentic experience.

If you'd like, I can help with specific restaurant suggestions, tips for avoiding crowds, or alternative activities tailored to your interests. Enjoy your trip to vibrant Singapore!"""
        display_conversation(local_message, "local_agent")
        time.sleep(1)
        
        # Language Assistant response
        language_message = """As you prepare for your trip to Singapore, here are some helpful language and communication tips:

**Language:**
- English is an official language and widely spoken, so communication should be easy.
- You'll also hear Mandarin Chinese, Malay, and Tamil spoken by locals.
- Singlish (Singaporean English) contains unique phrases and terms:
  - "Lah" added at the end of sentences for emphasis: "Can lah!" (Yes, it's possible!)
  - "Shiok" for expressing satisfaction or pleasure: "The food so shiok!" (The food is delicious!)
  - "Kiasu" describes the fear of missing out or losing out: "Don't be so kiasu, we'll get there on time."

**Cultural Communication:**
- Singaporeans are generally formal and polite in business settings.
- A slight bow or nod when greeting older people shows respect.
- Avoid pointing with your index finger (use your whole hand).
- Remove shoes when entering temples or someone's home.

**Practical Tips:**
- Download the SG BusLeh or Citymapper app for public transport directions.
- Signs are in English, making navigation simple.
- Most restaurants have English menus or pictures.
- Free Wi-Fi is widely available at MRT stations and malls.

Singapore's multicultural nature makes it very visitor-friendly, and most locals are happy to assist tourists if you need directions or recommendations. Enjoy your trip!"""
        display_conversation(language_message, "language_agent")
        time.sleep(1)
        
        # Currency Advisor response
        exchange_message = """Here's some essential financial information for your Singapore trip:

**Currency Information:**
- Singapore Dollar (SGD) is the local currency
- Current exchange rate: 1 USD ≈ 1.35 SGD
- Notes come in denominations of $2, $5, $10, $50, $100
- Coins are 5¢, 10¢, 20¢, 50¢, and $1

**Budget Breakdown (Standard):**
- Accommodation: 
  - Budget hotels: $80-120 SGD/night
  - Mid-range hotels: $120-200 SGD/night
  
- Food:
  - Hawker centers: $3-6 SGD per meal
  - Casual restaurants: $15-25 SGD per meal
  - Mid-range restaurants: $30-50 SGD per meal

- Transportation:
  - MRT/Bus rides: $0.90-2.50 SGD per trip
  - Tourist day pass: $10 SGD for unlimited rides
  - Taxi from airport to city: $20-30 SGD

- Attractions:
  - Gardens by the Bay domes: $28 SGD
  - Marina Bay Sands observation deck: $23 SGD
  - Singapore Zoo: $41 SGD

**Money-Saving Tips:**
- Use the MRT (subway) and buses for transportation
- Eat at hawker centers for authentic, affordable food
- Take advantage of free attractions (Supertree Grove light show, Merlion Park)
- Look for tourist passes that bundle attractions
- Many museums have free entry on certain evenings

**Payment Methods:**
- Credit cards are widely accepted
- ATMs are readily available throughout the city
- Most hawker centers are cash-only
- Mobile payments (Apple Pay, Google Pay) are common

For your 5-day trip with a standard budget, I'd recommend allocating approximately $700-900 SGD ($500-650 USD) for all expenses excluding accommodation and flights. Enjoy your trip to Singapore!"""
        display_conversation(exchange_message, "exchange_agent")
        time.sleep(1)
        
        # Travel Summary response
        summary_message = """# 🇸🇬 YOUR 5-DAY SINGAPORE ITINERARY 🇸🇬

## Overview:
This itinerary focuses on cultural experiences and food exploration with a standard budget of approximately SGD 150-200 ($110-150 USD) per day excluding accommodation.

## Day 1: Chinatown Cultural Immersion
- 🏨 **Accommodation**: Check into your hotel (Budget option: Hotel Boss or Hotel 81, around SGD 120/night)
- 🏯 **Morning**: Explore Chinatown's streets and markets
- 🏛️ **Afternoon**: Chinatown Heritage Centre (SGD 18) and Sri Mariamman Temple (free)
- 🍽️ **Meals**: Maxwell Food Centre for lunch (try Tian Tian Chicken Rice, SGD 5), Chinatown Food Street for dinner
- 🚇 **Transport**: MRT to Chinatown station, walking tour (buy EZ-Link card, SGD 12 including SGD 7 stored value)

## Day 2: Marina Bay & City Sights
- 🌆 **Morning**: Gardens by the Bay - Supertree Grove (free) and Cloud Forest & Flower Dome (SGD 28 for both domes)
- 🏙️ **Afternoon**: Walk along the Marina Bay waterfront to Merlion Park (free)
- 🌃 **Evening**: Marina Bay Sands light show (free, 8pm & 9pm)
- 🍽️ **Meals**: Satay by the Bay for lunch (SGD 10-15), Lau Pa Sat for dinner (SGD 10-15)
- 🚇 **Transport**: MRT and walking (approx. SGD 5-10)

## Day 3: Cultural Neighborhoods
- 🛕 **Morning**: Little India - Sri Veeramakaliamman Temple and local markets
- 🕌 **Afternoon**: Kampong Glam - Sultan Mosque and Haji Lane
- 🍽️ **Meals**: Breakfast at Tekka Centre (SGD 5), lunch at Islamic Restaurant (SGD 15), dinner at Arab Street stalls (SGD 10)
- 🚇 **Transport**: MRT between neighborhoods (approx. SGD 5-10)

## Day 4: Sentosa Island Adventure
- 🏝️ **Morning**: Travel to Sentosa via Boardwalk (free), explore beaches
- 🏰 **Afternoon**: Fort Siloso (free) and nature trails
- 🍽️ **Meals**: Seah Im Food Centre for breakfast (SGD 5), Malaysian Food Street on Sentosa for lunch (SGD 15), VivoCity Food Court for dinner (SGD 10)
- 🚇 **Transport**: MRT to HarbourFront + walking (approx. SGD 5)

## Day 5: Local Life & Markets
- 🏙️ **Morning**: Tiong Bahru heritage area and market
- 🛍️ **Afternoon**: Bugis Street Market for souvenirs
- 🍽️ **Meals**: Tiong Bahru Market for breakfast (try chwee kueh, SGD 3), lunch at Albert Centre Market (SGD 5-10)
- 🚇 **Transport**: MRT and walking (approx. SGD 5-10)
- ✈️ **Evening**: Departure

## Essential Practical Information:

### Currency: 
- SGD (Singapore Dollar), current rate approximately 1 USD = 1.35 SGD

### Transport Budget:
- Tourist Pass for unlimited travel: SGD 10/day
- OR EZ-Link stored value card with pay-per-trip (more economical for your itinerary)

### Food Budget:
- Breakfast: SGD 3-5 at hawker centers
- Lunch & Dinner: SGD 5-15 per meal at food courts and hawker centers
- Total food budget: Approximately SGD 25-40 per day

### Must-Try Local Dishes:
- Hainanese Chicken Rice
- Laksa
- Chili Crab (splurge item)
- Kaya Toast with Soft-boiled Eggs
- Char Kway Teow
- Satay

### Practical Tips:
- Download Grab app for occasional taxi needs
- Drinking water from taps is safe
- Carry an umbrella (for both sun and sudden rain)
- Most attractions open 9am-10pm
- Pre-book any special restaurants

This comprehensive itinerary balances cultural experiences, food exploration, and must-see attractions within your standard budget parameters. Enjoy your Singapore adventure!"""
        display_conversation(summary_message, "travel_summary_agent")

# ページ設定
st.set_page_config(
    page_title="Travel Planner AI Agent",
    page_icon="✈️",
    layout="wide"
)

# タイトルと説明
st.title("Travel Planner AI Agent")
st.markdown("Watch multiple AI agents collaborate to create your travel plan!")

# サイドバーにエージェントの説明を追加
with st.sidebar:
    st.header("Agent Descriptions")
    st.markdown("""
    <div style='background-color:#E6F7FF; padding:5px; border-radius:5px; margin-bottom:5px;'><b>User</b>: You</div>
    <div style='background-color:#F0F8EA; padding:5px; border-radius:5px; margin-bottom:5px;'><b>Travel Planner</b>: Creates the overall travel plan</div>
    <div style='background-color:#FFF8E1; padding:5px; border-radius:5px; margin-bottom:5px;'><b>Local Guide</b>: Suggests authentic attractions and activities</div>
    <div style='background-color:#F3E5F5; padding:5px; border-radius:5px; margin-bottom:5px;'><b>Language Assistant</b>: Provides language and cultural advice</div>
    <div style='background-color:#E0F7FA; padding:5px; border-radius:5px; margin-bottom:5px;'><b>Currency Advisor</b>: Offers information on currency and budget</div>
    <div style='background-color:#FFEBEE; padding:5px; border-radius:5px; margin-bottom:5px;'><b>Travel Summary</b>: Compiles the final travel plan</div>
    """, unsafe_allow_html=True)
    
    # 為替レート表示セクション
    st.header("Major Currency Exchange Rates")
    if st.button("Update Exchange Rates"):
        try:
            usd_rate = get_exchange_rate("USD")
            eur_rate = get_exchange_rate("EUR")
            gbp_rate = get_exchange_rate("GBP")
            
            st.markdown(f"""
            <div style='background-color:#E0F7FA; padding:10px; border-radius:5px;'>
                <p>USD/JPY: {usd_rate.get('exchange_rate', 'N/A')} yen</p>
                <p>EUR/JPY: {eur_rate.get('exchange_rate', 'N/A')} yen</p>
                <p>GBP/JPY: {gbp_rate.get('exchange_rate', 'N/A')} yen</p>
                <p><small>Last updated: {usd_rate.get('timestamp', 'N/A')}</small></p>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Failed to retrieve exchange rates: {e}")

    # Update the sidebar to add a more prominent demo button
    st.header("Quick Demo")
    if st.button("Show Singapore Travel Plan Demo", type="primary"):
        conversation_container = st.container()
        show_demo_conversation()

# 2カラムレイアウトの設定
col1, col2 = st.columns([2, 3])

with col1:
    st.header("Travel Request")
    
    # テキスト入力
    initial_message = st.text_area(
        "Please describe your travel plans in detail:",
        height=150,
        placeholder="Example: I'm planning a one-week trip to Malaysia. I'd like to visit Kuala Lumpur and Penang Island. My budget is around 1,500 USD, and I'm interested in food and cultural experiences."
    )
    
    # ユーザープロファイル情報
    st.subheader("User Profile (Optional)")
    age = st.slider("Age", 18, 80, 30)
    travel_style = st.multiselect(
        "Travel Style", 
        ["Cultural Experience", "Nature", "Food", "Adventure", "Relaxation", "Shopping", "History"],
        ["Cultural Experience", "Food"]
    )
    budget_level = st.select_slider(
        "Budget Level",
        options=["Budget", "Affordable", "Standard", "Luxury", "Ultra-Luxury"],
        value="Standard"
    )
    
    # プロファイル情報を初期メッセージに追加
    def append_profile_info(message):
        profile = f"\n\n[Profile Information] Age: {age}, Travel Style: {', '.join(travel_style)}, Budget: {budget_level}"
        return message + profile if message else profile
    
    # 送信ボタン
    if st.button("Generate Travel Plan", type="primary"):
        if initial_message:
            # プロファイル情報を追加
            complete_message = append_profile_info(initial_message)
            
            with col2:
                # 会話表示用のコンテナ
                conversation_container = st.container()
                st.header("Agent Conversation")
                
                with st.spinner("AI agents are creating your travel plan..."):
                    # 初期メッセージの表示
                    display_conversation(complete_message, "user_proxy")
                    
                    # 会話を開始
                    user_proxy.initiate_chat(
                        manager,
                        message=complete_message
                    )
                    
                    # 会話履歴を表示
                    for message in groupchat.messages:
                        if message.get('name'):
                            role = message.get('name')
                        else:
                            role = message.get('role', 'Unknown')
                        content = message.get('content', '')
                        display_conversation(content, role)
        else:
            st.warning("Please enter your travel request first.")

with col2:
    if not initial_message:
        st.header("Agent Conversation")
        st.info("Enter your travel request in the form on the left and click 'Generate Travel Plan' to see the AI agents' conversation here.")
        
        # デモ画像表示
        st.image("https://via.placeholder.com/800x400.png?text=Travel+Planning+Agents+Visualization", 
                 caption="Example of agent conversation")

# フッター
st.markdown("---")
st.markdown("Powered by Azure OpenAI and AutoGen | © 2023 Travel AI Planner")

# アプリケーション終了時にクライアントを閉じる
def cleanup():
    client.close()

# Streamlitの終了時にクリーンアップを実行
atexit.register(cleanup) 