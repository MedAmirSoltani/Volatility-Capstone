from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd
from datetime import datetime, timedelta
from .models import MT5Candle,Preferences,Trade
from django.utils import timezone
from .forms import CustomUserCreationForm, CustomAuthenticationForm,CustomUserChangeForm,PreferencesForm
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
import plotly.graph_objs as go
from plotly.offline import plot
from django.conf import settings
import os
import joblib
from django.shortcuts import get_object_or_404
from decimal import Decimal


import requests
from textblob import TextBlob
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
@api_view(['POST'])
def fetch_mt5_15min(request):
    symbol = request.data.get("symbol", "EURUSD")
    from_date_str = request.data.get("from")
    to_date_str = request.data.get("to")

    if not from_date_str or not to_date_str:
        return Response({"error": "Missing 'from' or 'to' parameters"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
        to_date = datetime.strptime(to_date_str, "%Y-%m-%d")
    except ValueError:
        return Response({"error": "Invalid date format, use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        MT5_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
        if not mt5.initialize(path=MT5_PATH):
            return Response({"error": f"MT5 init failed: {mt5.last_error()}"}, status=500)

        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, from_date, to_date)
        mt5.shutdown()

        if rates is None or len(rates) == 0:
            return Response({"error": "No data found"}, status=404)

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "tick_volume"]]

        return Response(df.to_dict(orient="records"), status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

#----------------------------------------------------------------------------------



@api_view(['GET'])
def fetch_2025_15min(request):
    symbol = request.query_params.get("symbol", "EURUSD")
    from_date = datetime(2025, 1, 1)
    to_date = datetime(2025, 12, 31)

    try:
        MT5_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
        if not mt5.initialize(path=MT5_PATH):
            return Response({"error": f"MT5 init failed: {mt5.last_error()}"}, status=500)

        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, from_date, to_date)
        mt5.shutdown()

        if rates is None or len(rates) == 0:
            return Response({"error": "No data found"}, status=404)

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "tick_volume"]]

        saved = 0
        for _, row in df.iterrows():
            obj, created = MT5Candle.objects.get_or_create(
                symbol=symbol,
                time=row["time"],
                defaults={
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "tick_volume": row["tick_volume"]
                }
            )
            if created:
                saved += 1

        return Response({"status": "success", "saved_candles": saved}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

#-----------------------------------------------------------------------
@api_view(['GET'])
def fetch_latest_15min(request):
    symbol = request.query_params.get("symbol", "EURUSD")

    try:
        MT5_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
        if not mt5.initialize(path=MT5_PATH):
            return Response({"error": f"MT5 init failed: {mt5.last_error()}"}, status=500)

        # Get the latest datetime in DB
        last_record = MT5Candle.objects.filter(symbol=symbol).order_by('-time').first()
        if last_record:
            from_date = last_record.time + timedelta(minutes=15)
        else:
            from_date = timezone.now() - timedelta(days=1)

        to_date = timezone.now()

        if from_date >= to_date:
            mt5.shutdown()
            return Response({"message": "No new data to fetch."}, status=200)

        # Convert to naive datetime for MT5
        from_date_naive = from_date.replace(tzinfo=None)
        to_date_naive = to_date.replace(tzinfo=None)

        # Fetch MT5 data
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, from_date_naive, to_date_naive)
        mt5.shutdown()

        if rates is None or len(rates) == 0:
            return Response({"message": "No new candles found in MT5."}, status=404)

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "tick_volume"]]

        saved = 0
        for _, row in df.iterrows():
            aware_time = timezone.make_aware(row["time"])
            exists = MT5Candle.objects.filter(symbol=symbol, time=aware_time).exists()
            if not exists:
                MT5Candle.objects.create(
                    symbol=symbol,
                    time=aware_time,
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    tick_volume=row["tick_volume"]
                )
                saved += 1

        return Response({"status": "success", "new_candles_saved": saved}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
    


#WEB-------------------    

import plotly.graph_objs as go
from plotly.offline import plot
from django.shortcuts import render
from .models import MT5Candle

def home(request):
    # Get selected plot type from query parameter
    plot_type = request.GET.get('plot_type', 'candlestick')

    # Get last 50 points for EURUSD
    candles = MT5Candle.objects.filter(symbol="EURUSD").order_by('-time')[:96][::-1]
    timestamps = [c.time.strftime('%Y-%m-%d %H:%M') for c in candles]
    open_prices = [c.open for c in candles]
    high_prices = [c.high for c in candles]
    low_prices = [c.low for c in candles]
    close_prices = [c.close for c in candles]
    volumes = [c.tick_volume for c in candles]

    if plot_type == "line":
        trace = go.Scatter(x=timestamps, y=close_prices, mode='lines+markers', name='Close Price')
    elif plot_type == "ohlc":
        trace = go.Ohlc(x=timestamps, open=open_prices, high=high_prices, low=low_prices, close=close_prices, name='OHLC')
    elif plot_type == "volume":
        trace = go.Bar(x=timestamps, y=volumes, name='Volume', marker_color='orange')
    else:  # Default to candlestick
        trace = go.Candlestick(x=timestamps, open=open_prices, high=high_prices, low=low_prices, close=close_prices, name='Candlestick')

    layout = go.Layout(
        title=f'{plot_type.capitalize()} Chart for EUR/USD',
        xaxis=dict(title='Time', rangeslider=dict(visible=(plot_type == "candlestick" or plot_type == "ohlc"))),
        yaxis=dict(title='Price' if plot_type != "volume" else 'Volume'),
        height=600
    )

    fig = go.Figure(data=[trace], layout=layout)
    plot_div = plot(fig, output_type='div', include_plotlyjs=True)

    return render(request, 'home.html', {
        'plot_div': plot_div,
        'selected_type': plot_type
    })




def user_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('loading')
            else:
                # Return an 'invalid login' error message
                pass
    else:
        form = CustomAuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})



def loading(request):
    return render(request, 'loading.html')



def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Redirect to login page after successful registration
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def how(request):
    return render(request, 'how.html')
def about(request):
    return render(request, 'about.html')





import requests

def call_mistral_summary(volatility_values, sentiment_summary):
    # Format the input data for LLM
    volatility_trend = f"{[round(v, 3) for v in volatility_values[-5:]]}"

    prompt = f"""
You are a professional financial assistant specialized in Forex market analysis.

You are provided with:
- The latest predicted volatility values for EUR/USD: {volatility_trend}
- Recent news sentiment analysis:
  • Positive: {sentiment_summary['positive']}%
  • Neutral: {sentiment_summary['neutral']}%
  • Negative: {sentiment_summary['negative']}%

Your task is to:
1. Summarize the current market conditions in a clear and concise way.
2. Provide a **trading recommendation** (Buy, Sell, or Hold) with a short justification based on the analysis.
dont answer with tables
Write like a senior analyst giving guidance to a trader. Be objective and actionable.
"""

    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return "Erreur lors de l'analyse LLM : " + str(e)






def dashboard(request):
    # 1. Load all data from DB ordered by ID (time)
    qs_all = MT5Candle.objects.filter(symbol="EURUSD").order_by('id')
    df_all = pd.DataFrame.from_records(qs_all.values('time', 'close'))

    if df_all.empty or len(df_all) < 100:
        return render(request, 'dashboard.html', {'error': 'Not enough data in MT5Candle table.'})

    # 2. Compute returns (% change) on full data
    df_all['close'] = 100 * df_all['close'].pct_change()
    df_all = df_all.dropna()
    df_all = df_all[df_all['close'] != 0]

    # 3. Compute rolling std for volatility (shifted to simulate prediction target)
    df_all['volatility'] = df_all['close'].rolling(window=16, min_periods=16).std().shift(-16)
    df_all = df_all.dropna().copy()

    # 4. Time-based features
    df_all['dayofweek'] = df_all['time'].dt.dayofweek
    df_all['dayofmonth'] = df_all['time'].dt.day
    df_all['dayofyear'] = df_all['time'].dt.dayofyear

    # 5. Lag features
    df_all['prev1'] = df_all['volatility'].shift(1)
    df_all['prev2'] = df_all['volatility'].shift(2)
    df_all['prev3'] = df_all['volatility'].shift(3)
    df_all['prev4'] = df_all['volatility'].shift(4)
    df_all = df_all.dropna().copy()

    # 6. Get only last 1 day for display
    last_date = df_all['time'].max().date()
    df_display = df_all[df_all['time'].dt.date == last_date].copy()

    # 7. Load trained model
    model_path = os.path.join(settings.BASE_DIR, 'mt5data', 'static', 'models', 'xgboost_model.pkl')
    model = joblib.load(model_path)

    # 8. Prepare recent last 4 rows for prediction chain
    recent = df_all[['time', 'volatility']].copy().tail(4)
    if len(recent) < 4:
        return render(request, 'dashboard.html', {'error': 'Not enough recent data for prediction.'})

    predictions, forecast_dates = [], []

    # 9. Predict 16 future volatility points
    for _ in range(16):
        next_time = recent['time'].iloc[-1] + timedelta(minutes=15)

        input_data = pd.DataFrame([{
            'prev1': recent['volatility'].iloc[-1],
            'prev4': recent['volatility'].iloc[-4],
            'prev2': recent['volatility'].iloc[-2],
            'prev3': recent['volatility'].iloc[-3],

            'dayofyear': next_time.dayofyear,
            'dayofmonth': next_time.day,
            'dayofweek': next_time.weekday()
        }])

        pred = model.predict(input_data)[0]
        predictions.append(pred)
        forecast_dates.append(next_time)

        # Update recent for next prediction
        new_row = pd.DataFrame([{
            'time': next_time,
            'volatility': pred
        }])
        recent = pd.concat([recent, new_row], ignore_index=True)

    # 10. Plot actual + forecast
    trace_actual = go.Scatter(
        x=df_display['time'],
        y=df_display['volatility'],
        mode='lines',
        name='Actual Volatility',
        line=dict(color='green')
    )

    trace_forecast = go.Scatter(
        x=forecast_dates,
        y=predictions,
        mode='lines+markers',
        name='Predicted Volatility (next 4h)',
        line=dict(color='blue')
    )

    fig = go.Figure(data=[trace_actual, trace_forecast])
    fig.update_layout(
        title='Volatility Forecast using XGBoost',
        xaxis_title='Time',
        yaxis_title='Volatility (%)',
        height=600,
        xaxis_rangeslider_visible=True
    )
    latest_point = MT5Candle.objects.filter(symbol="EURUSD").latest("id")
        # --- News Sentiment Analysis (for dashboard preview) ---
    NEWSAPI_KEY = "da8e2e705b914f9f86ed2e9692e66012"
    sentiment_url = f"https://newsapi.org/v2/everything?q=eurusd OR ecb OR forex OR usd OR inflation&language=en&sortBy=publishedAt&pageSize=50&apiKey={NEWSAPI_KEY}"
    try:
        news_response = requests.get(sentiment_url)
        news_articles = news_response.json().get('articles', [])
    except Exception as e:
        news_articles = []

    sentiment_scores = []
    for article in news_articles:
        text = article.get('content') or article.get('description') or ''
        polarity = TextBlob(text).sentiment.polarity if text else 0
        sentiment_scores.append(polarity)

    pos_count = sum(1 for s in sentiment_scores if s > 0.2)
    neg_count = sum(1 for s in sentiment_scores if s < -0.2)
    neutral_count = len(sentiment_scores) - pos_count - neg_count
    total = len(sentiment_scores) or 1  # prevent division by zero

    sentiment_summary = {
        'positive': round(pos_count / total * 100, 1),
        'neutral': round(neutral_count / total * 100, 1),
        'negative': round(neg_count / total * 100, 1),
    }
    llm_summary = call_mistral_summary(predictions, sentiment_summary)

    context = {
        'llm_summary': llm_summary,  
        'sentiment_summary': sentiment_summary,
        'plotly_chart': fig.to_json(),
        'open_price': latest_point.open,
        'close_price': latest_point.close,
        'tick_volume': latest_point.tick_volume
    }



    
    return render(request, 'dashboard.html', context)



def sentiment_analysis(request):
    NEWSAPI_KEY = "da8e2e705b914f9f86ed2e9692e66012"
    url = f"https://newsapi.org/v2/everything?q=eurusd OR ecb OR forex OR usd OR inflation&language=en&sortBy=publishedAt&pageSize=50&apiKey={NEWSAPI_KEY}"

    try:
        response = requests.get(url)
        articles = response.json().get('articles', [])
    except Exception as e:
        return render(request, 'sentiment_analysis.html', {
            'error': 'Could not fetch news. Please check your connection or API key.'
        })

    data = []
    for article in articles:
        content = article.get('content') or article.get('description') or ''
        sentiment_score = TextBlob(content).sentiment.polarity if content else 0

        data.append({
            'title': article.get('title'),
            'source': article.get('source', {}).get('name'),
            'published_at': article.get('publishedAt'),
            'description': article.get('description'),
            'url': article.get('url'),
            'sentiment_score': sentiment_score
        })

    # Pagination (5 per page)
    paginator = Paginator(data, 5)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'sentiment_analysis.html', {'page_obj': page_obj})





def profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')  # Redirect back to the profile page after saving
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, 'profile.html', {'form': form})



def preferences(request):
    if request.method == 'POST':
        form = PreferencesForm(request.POST)
        if form.is_valid():
            preferences = form.save(commit=False)
            preferences.user = request.user
            preferences.save()
            
            # Assign preferences to the user and save the user instance
            request.user.preferences = preferences
            request.user.save()
            
            return redirect('home')  # Redirect to dashboard or any other page
    else:
        form = PreferencesForm()
    return render(request, 'preferences.html', {'form': form})

def update_preferences(request):
    try:
        preferences = Preferences.objects.get(user=request.user)
    except Preferences.DoesNotExist:
        return redirect('preferences')  # Redirect to create preferences if they don't exist

    if request.method == 'POST':
        form = PreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            return redirect('home')  # Redirect to dashboard or any other page
    else:
        form = PreferencesForm(instance=preferences)

    return render(request, 'update_preferences.html', {'form': form})

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def trading_strategies(request):
    # Dummy data for demonstration (trading strategies)
    trading_strategies_info = [
    {'Name': 'Introduction to Trading', 'Objective': 'Getting started with trading fundamentals', 'Image': '/static/images/intro.jpg', 'Description': "Trading is the art of buying and selling financial assets, such as stocks, bonds, currencies, and commodities, with the aim of making a profit. It involves analyzing market data, identifying opportunities, and executing trades based on various strategies like the ones mentioned above. Whether you're a seasoned investor or a novice trader, understanding these strategies can help you navigate the complex world of financial markets more effectively. Happy trading!"},
    {'Name': 'Momentum Strategy', 'Objective': 'Maximizing returns', 'Image': '/static/images/mom.jpg', 'Description': "Imagine you're at a sports event, witnessing a team on an impressive winning streak. Momentum traders operate much like enthusiastic fans cheering for the team with consistent victories. They rely on the principle that assets exhibiting recent positive price movements are likely to continue rising, while those with negative movements are expected to keep falling. This strategy is grounded in the idea that markets tend to follow trends, and once a trend is established, it's likely to persist for a certain period. Momentum traders use technical indicators like Relative Strength Index (RSI) or Moving Average Convergence Divergence (MACD) to identify assets with strong momentum. For instance, if a stock has been steadily climbing in price over the past few weeks, a momentum trader might buy it, expecting the upward trend to continue. However, it's essential for momentum traders to exercise caution, as momentum can quickly shift, leading to abrupt reversals in price direction."},
    {'Name': 'Mean Reversion Strategy', 'Objective': 'Minimizing volatility', 'Image': '/static/images/mr.jpg', 'Description': "Picture a rubber band being stretched to its limit; eventually, it snaps back to its original position. Mean reversion traders operate on a similar principle, believing that asset prices tend to move back towards their historical average over time. When an asset's price strays too far from its mean, these traders see it as an opportunity to buy low or sell high. The strategy is based on the assumption that markets often exhibit short-term fluctuations around a long-term equilibrium or average price. For example, if a stock's price has dropped significantly below its long-term average, a mean reversion trader might buy it, anticipating a return to its average price. However, it's crucial for mean reversion traders to carefully assess whether the price deviation from the mean is a temporary anomaly or a sign of a fundamental change in the asset's value."},
    {'Name': 'Trend Following Strategy', 'Objective': 'Identifying and riding trends', 'Image': '/static/images/tf.jpg', 'Description': "Imagine riding a wave at the beach; you catch the wave's momentum and ride it until it begins to lose strength. Trend following traders operate similarly, aiming to profit from sustained price movements in a particular direction. They identify trends using technical analysis tools like moving averages or trendlines. When they spot an upward trend, they buy assets with the expectation that prices will continue to rise. Conversely, during a downtrend, they sell assets, anticipating further declines. Trend following strategies are based on the belief that markets exhibit momentum, and once a trend is established, it's likely to continue for a significant period. However, it's essential for trend followers to be mindful of potential reversals and to implement risk management measures to protect against adverse market movements."},
    {'Name': 'Arbitrage Strategy', 'Objective': 'Exploiting price inefficiencies', 'Image': '/static/images/ar.jpg', 'Description': "Imagine finding the same product selling for different prices in two different stores; you buy it from the cheaper store and sell it at the higher-priced one, pocketing the price difference as profit. Arbitrageurs exploit price discrepancies between different markets or assets to make risk-free profits. This strategy relies on the principle of the law of one price, which states that identical goods should have the same price when expressed in a common currency. For example, if a stock is trading at $50 on one exchange and $52 on another, an arbitrageur might buy it on the cheaper exchange and simultaneously sell it on the more expensive one, profiting from the price difference. However, arbitrage opportunities are typically short-lived and require swift execution to capitalize on price disparities before they disappear."},
    {'Name': 'Contrarian Strategy', 'Objective': 'Capitalizing on market reversals', 'Image': '/static/images/cs.jpg', 'Description': "Envision swimming against the current in a river; while others are being carried downstream, you're moving in the opposite direction. Contrarian traders go against prevailing market sentiment, buying when others are selling and selling when others are buying. They believe that markets often overreact to news or events, creating opportunities to profit from sentiment shifts. Contrarian strategies are based on the premise that market sentiment tends to be cyclical, swinging between optimism and pessimism. For instance, if a stock's price plunges due to negative news, a contrarian trader might see it as an opportunity to buy low, expecting the price to rebound as market sentiment improves. However, contrarian trading requires a contrarian mindset and the ability to withstand periods of short-term market volatility."},
    {'Name': 'Breakout Strategy', 'Objective': 'Capitalizing on price breakouts', 'Image': '/static/images/bs.jpg', 'Description': "Imagine a dam bursting; once the barrier is broken, water rushes through with force. Breakout traders aim to capitalize on significant price movements that occur when an asset breaches support or resistance levels. They wait for a breakout, where the price moves above resistance or below support, signaling a potential trend continuation. Breakout strategies are based on the premise that price movements tend to accelerate following a breakout, as traders rush to capitalize on the new trend. For example, if a stock's price breaks above a key resistance level, breakout traders might buy it, anticipating further upward movement. However, breakout trading carries inherent risks, including false breakouts and whipsaw movements, requiring traders to implement strict risk management measures."},
    {'Name': 'Swing Trading Strategy', 'Objective': 'Profiting from short- to medium-term price swings', 'Image': '/static/images/sw.jpg', 'Description': "Picture a pendulum swinging back and forth; swing traders aim to profit from the market's natural ebb and flow. They identify short- to medium-term price swings within a larger trend and capitalize on them. Swing traders typically hold positions for a few days to several weeks, buying at swing lows and selling at swing highs. Swing trading strategies are based on the premise that markets often exhibit periodic fluctuations within a broader trend, providing opportunities for short-term profits. For instance, if a stock's price experiences a short-term dip within an overall uptrend, a swing trader might buy it, expecting the price to bounce back as the trend resumes. However, swing trading requires discipline and patience, as traders must wait for opportune entry and exit points to maximize profitability."},
    ]


    # Fetch user preferences (assuming one-to-one relationship between CustomUser and Preferences)
    user_preferences = None
    if request.user.is_authenticated:
        user_preferences = Preferences.objects.filter(user=request.user).first()

    # Analyze user preferences and recommend the best course
    recommended_courses = recommend_course(user_preferences)

    # Filter out the recommended courses
    recommended_strategies = []
    for course in recommended_courses:
        recommended_strategies += [strategy for strategy in trading_strategies_info if strategy['Name'] == course]

    # Paginate the courses
    paginator = Paginator(recommended_strategies, 1)  # Show 5 courses per page
    page = request.GET.get('page')
    try:
        recommended_strategies = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        recommended_strategies = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        recommended_strategies = paginator.page(paginator.num_pages)

    return render(request, 'trading_strategies.html', {'trading_strategies_info': recommended_strategies, 'recommended_course': recommended_courses})

def recommend_course(preferences):
    if not preferences:
        return ['Introduction to Trading']  # Default recommendation if preferences are not available

    # Analyze user preferences and recommend the best courses based on their preferences
    risk_tolerance = preferences.risk_tolerance
    investment_horizon = preferences.investment_horizon
    investment_objective = preferences.investment_objective
    knowledge_experience = preferences.knowledge_experience

    recommended_strategies = []

    if risk_tolerance == 'high':
        if investment_horizon == 'long_term':
            recommended_strategies.append('Mean Reversion Strategy')
            recommended_strategies.append('Trend Following Strategy')
        if investment_horizon == 'medium_term':
            recommended_strategies.append('Trend Following Strategy')
            recommended_strategies.append('Swing Trading Strategy')
        recommended_strategies.append('Momentum Strategy')
        recommended_strategies.append('Arbitrage Strategy')

    elif risk_tolerance == 'medium':
        if investment_objective == 'capital_preservation':
            recommended_strategies.append('Mean Reversion Strategy')
            recommended_strategies.append('Swing Trading Strategy')
        if investment_objective == 'income_generation':
            recommended_strategies.append('Trend Following Strategy')
            recommended_strategies.append('Arbitrage Strategy')
        recommended_strategies.append('Momentum Strategy')
        recommended_strategies.append('Breakout Strategy')

    else:  # Low risk tolerance
        if knowledge_experience == 'advanced':
            recommended_strategies.append('Mean Reversion Strategy')
            recommended_strategies.append('Breakout Strategy')
        else:
            recommended_strategies.append('Momentum Strategy')
            recommended_strategies.append('Introduction to Trading')

    return recommended_strategies



def allcourses(request):
    # Dummy data for demonstration (trading strategies)
    trading_strategies_info = [
    {'Name': 'Introduction to Trading', 'Objective': 'Getting started with trading fundamentals', 'Image': '/static/images/intro.jpg', 'Description': "Trading is the art of buying and selling financial assets, such as stocks, bonds, currencies, and commodities, with the aim of making a profit. It involves analyzing market data, identifying opportunities, and executing trades based on various strategies like the ones mentioned above. Whether you're a seasoned investor or a novice trader, understanding these strategies can help you navigate the complex world of financial markets more effectively. Happy trading!"},

    {'Name': 'Momentum Strategy', 'Objective': 'Maximizing returns', 'Image': '/static/images/mom.jpg', 'Description': "Imagine you're at a sports event, witnessing a team on an impressive winning streak. Momentum traders operate much like enthusiastic fans cheering for the team with consistent victories. They rely on the principle that assets exhibiting recent positive price movements are likely to continue rising, while those with negative movements are expected to keep falling. This strategy is grounded in the idea that markets tend to follow trends, and once a trend is established, it's likely to persist for a certain period. Momentum traders use technical indicators like Relative Strength Index (RSI) or Moving Average Convergence Divergence (MACD) to identify assets with strong momentum. For instance, if a stock has been steadily climbing in price over the past few weeks, a momentum trader might buy it, expecting the upward trend to continue. However, it's essential for momentum traders to exercise caution, as momentum can quickly shift, leading to abrupt reversals in price direction."},
    {'Name': 'Mean Reversion Strategy', 'Objective': 'Minimizing volatility', 'Image': '/static/images/mr.jpg', 'Description': "Picture a rubber band being stretched to its limit; eventually, it snaps back to its original position. Mean reversion traders operate on a similar principle, believing that asset prices tend to move back towards their historical average over time. When an asset's price strays too far from its mean, these traders see it as an opportunity to buy low or sell high. The strategy is based on the assumption that markets often exhibit short-term fluctuations around a long-term equilibrium or average price. For example, if a stock's price has dropped significantly below its long-term average, a mean reversion trader might buy it, anticipating a return to its average price. However, it's crucial for mean reversion traders to carefully assess whether the price deviation from the mean is a temporary anomaly or a sign of a fundamental change in the asset's value."},
    {'Name': 'Trend Following Strategy', 'Objective': 'Identifying and riding trends', 'Image': '/static/images/tf.jpg', 'Description': "Imagine riding a wave at the beach; you catch the wave's momentum and ride it until it begins to lose strength. Trend following traders operate similarly, aiming to profit from sustained price movements in a particular direction. They identify trends using technical analysis tools like moving averages or trendlines. When they spot an upward trend, they buy assets with the expectation that prices will continue to rise. Conversely, during a downtrend, they sell assets, anticipating further declines. Trend following strategies are based on the belief that markets exhibit momentum, and once a trend is established, it's likely to continue for a significant period. However, it's essential for trend followers to be mindful of potential reversals and to implement risk management measures to protect against adverse market movements."},
    {'Name': 'Arbitrage Strategy', 'Objective': 'Exploiting price inefficiencies', 'Image': '/static/images/ar.jpg', 'Description': "Imagine finding the same product selling for different prices in two different stores; you buy it from the cheaper store and sell it at the higher-priced one, pocketing the price difference as profit. Arbitrageurs exploit price discrepancies between different markets or assets to make risk-free profits. This strategy relies on the principle of the law of one price, which states that identical goods should have the same price when expressed in a common currency. For example, if a stock is trading at $50 on one exchange and $52 on another, an arbitrageur might buy it on the cheaper exchange and simultaneously sell it on the more expensive one, profiting from the price difference. However, arbitrage opportunities are typically short-lived and require swift execution to capitalize on price disparities before they disappear."},
    {'Name': 'Contrarian Strategy', 'Objective': 'Capitalizing on market reversals', 'Image': '/static/images/cs.jpg', 'Description': "Envision swimming against the current in a river; while others are being carried downstream, you're moving in the opposite direction. Contrarian traders go against prevailing market sentiment, buying when others are selling and selling when others are buying. They believe that markets often overreact to news or events, creating opportunities to profit from sentiment shifts. Contrarian strategies are based on the premise that market sentiment tends to be cyclical, swinging between optimism and pessimism. For instance, if a stock's price plunges due to negative news, a contrarian trader might see it as an opportunity to buy low, expecting the price to rebound as market sentiment improves. However, contrarian trading requires a contrarian mindset and the ability to withstand periods of short-term market volatility."},
    {'Name': 'Breakout Strategy', 'Objective': 'Capitalizing on price breakouts', 'Image': '/static/images/bs.jpg', 'Description': "Imagine a dam bursting; once the barrier is broken, water rushes through with force. Breakout traders aim to capitalize on significant price movements that occur when an asset breaches support or resistance levels. They wait for a breakout, where the price moves above resistance or below support, signaling a potential trend continuation. Breakout strategies are based on the premise that price movements tend to accelerate following a breakout, as traders rush to capitalize on the new trend. For example, if a stock's price breaks above a key resistance level, breakout traders might buy it, anticipating further upward movement. However, breakout trading carries inherent risks, including false breakouts and whipsaw movements, requiring traders to implement strict risk management measures."},
    {'Name': 'Swing Trading Strategy', 'Objective': 'Profiting from short- to medium-term price swings', 'Image': '/static/images/sw.jpg', 'Description': "Picture a pendulum swinging back and forth; swing traders aim to profit from the market's natural ebb and flow. They identify short- to medium-term price swings within a larger trend and capitalize on them. Swing traders typically hold positions for a few days to several weeks, buying at swing lows and selling at swing highs. Swing trading strategies are based on the premise that markets often exhibit periodic fluctuations within a broader trend, providing opportunities for short-term profits. For instance, if a stock's price experiences a short-term dip within an overall uptrend, a swing trader might buy it, expecting the price to bounce back as the trend resumes. However, swing trading requires discipline and patience, as traders must wait for opportune entry and exit points to maximize profitability."}
]

    # Paginate the courses
    paginator = Paginator(trading_strategies_info, 1)  # Show 1 strategy per page
    page = request.GET.get('page')
    try:
        trading_strategies_info = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        trading_strategies_info = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        trading_strategies_info = paginator.page(paginator.num_pages)

    return render(request, 'allcourses.html', {'trading_strategies_info': trading_strategies_info})


import requests
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def chat_interface(request):
    if request.method == "POST":
        user_message = request.POST.get("message", "")
        if not user_message:
            return JsonResponse({"response": "Please enter a message."})

        # Prepare Groq LLM call
        prompt = f"""
You are ArtSmart, a finance chatbot created by Amir Soltani.
You specialize in trading, with a primary focus on Forex (dont answer with tables). Respond in a professional, clear, and helpful manner to the following user query:

User: "{user_message}"
ArtSmart:"""

        headers = {
            "Authorization": "Bearer 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",
            "Content-Type": "application/json"
        }

        data = {
            "model": "openai/gpt-oss-120b",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 1000,
            
        }

        try:
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
            reply = response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            reply = f"⚠️ An error occurred while fetching response: {str(e)}"

        return JsonResponse({"response": reply})

    return render(request, "chat.html")




import numpy as np
import pandas as pd

def market_insights(request):
    plot_type = request.GET.get('plot_type', 'candlestick')
    deviation_options = [0, 1, 2, 3, 4, 5, 6, 7, 8]

    # Indicator toggles from frontend
    show_ma10 = request.GET.get('show_ma10') == 'on'
    show_ma30 = request.GET.get('show_ma30') == 'on'
    show_rsi = request.GET.get('show_rsi') == 'on'
    show_macd = request.GET.get('show_macd') == 'on'

    candles = MT5Candle.objects.filter(symbol="EURUSD").order_by('-time')[:96][::-1]

    df = pd.DataFrame({
        'timestamp': [c.time for c in candles],
        'open': [c.open for c in candles],
        'high': [c.high for c in candles],
        'low': [c.low for c in candles],
        'close': [c.close for c in candles],
        'volume': [c.tick_volume for c in candles]
    })

    traces = []

    if plot_type == "line":
        traces.append(go.Scatter(x=df['timestamp'], y=df['close'], mode='lines+markers', name='Close Price'))
    elif plot_type == "ohlc":
        traces.append(go.Ohlc(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='OHLC'))
    elif plot_type == "volume":
        traces.append(go.Bar(x=df['timestamp'], y=df['volume'], name='Volume', marker_color='orange'))
    else:
        traces.append(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Candlestick'))

    # ➕ Add indicators if selected
    if show_ma10:
        df['ma10'] = df['close'].rolling(window=10).mean()
        traces.append(go.Scatter(x=df['timestamp'], y=df['ma10'], mode='lines', name='MA10', line=dict(color='blue', dash='dot')))
    if show_ma30:
        df['ma30'] = df['close'].rolling(window=30).mean()
        traces.append(go.Scatter(x=df['timestamp'], y=df['ma30'], mode='lines', name='MA30', line=dict(color='green', dash='dash')))
    if show_rsi:
        delta = df['close'].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).rolling(window=14).mean()
        avg_loss = pd.Series(loss).rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        traces.append(go.Scatter(x=df['timestamp'], y=df['rsi'], mode='lines', name='RSI', yaxis='y2', line=dict(color='purple')))

    if show_macd:
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        signal = df['macd'].ewm(span=9, adjust=False).mean()
        traces.append(go.Scatter(x=df['timestamp'], y=df['macd'], mode='lines', name='MACD', yaxis='y2', line=dict(color='red')))
        traces.append(go.Scatter(x=df['timestamp'], y=signal, mode='lines', name='Signal', yaxis='y2', line=dict(color='orange')))

    layout = go.Layout(
        title=f'{plot_type.capitalize()} Chart for EUR/USD',
        xaxis=dict(title='Time', rangeslider=dict(visible=(plot_type in ["candlestick", "ohlc"]))),
        yaxis=dict(title='Price'),
        height=600
    )

    if show_rsi or show_macd:
        layout.update(yaxis2=dict(title='RSI / MACD', overlaying='y', side='right'))

    fig = go.Figure(data=traces, layout=layout)
    plot_div = plot(fig, output_type='div', include_plotlyjs=True)

    # Order execution logic
    message = None
    user_prefs = Preferences.objects.first()

    if request.method == 'POST':
        volume = Decimal(request.POST.get('volume', '0') or '0')
        action = request.POST.get('action')

        if not user_prefs:
            message = "⚠️ Preferences not set."
        else:
            price = Decimal(str(df['close'].iloc[-1])) if not df.empty else Decimal('0')
            cost = price * volume

            if action == 'buy':
                if user_prefs.available_funds >= cost:
                    user_prefs.available_funds -= cost
                    user_prefs.save()
                    Trade.objects.create(user=request.user, action='buy', volume=volume, price=price, time=timezone.now(), profit=Decimal('0.00'), closed=False)
                    message = f"✅ Buy order executed for {volume} lots at {price:.5f}"
                else:
                    message = "❌ Insufficient funds to execute buy order."
            elif action == 'sell':
                user_prefs.available_funds += cost
                user_prefs.save()
                Trade.objects.create(user=request.user, action='sell', volume=volume, price=price, time=timezone.now(), profit=Decimal('0.00'), closed=False)
                message = f"✅ Sell order executed for {volume} lots at {price:.5f}"
            else:
                message = "⚠️ Invalid action."

    trade_history = Trade.objects.filter(user=request.user).order_by('-time')
    bid, ask = get_live_bid_ask()

    return render(request, 'market_insights.html', {
        'plot_div': plot_div,
        'selected_type': plot_type,
        'deviation_options': deviation_options,
        'message': message,
        'available_funds': user_prefs.available_funds if user_prefs else 0,
        'bid': bid,
        'ask': ask,
        'trade_history': trade_history,
        'show_ma10': show_ma10,
        'show_ma30': show_ma30,
        'show_rsi': show_rsi,
        'show_macd': show_macd
    })



def close_trade(request, trade_id):
    trade = get_object_or_404(Trade, id=trade_id, user=request.user, closed=False)
    user_prefs = trade.user.preferences

    if trade.action == 'buy':
        # Simulate sell at current price (no price update logic for simplicity)
        close_price = trade.price
        profit = close_price * trade.volume  # You can improve this with real pricing
        user_prefs.available_funds += profit
    elif trade.action == 'sell':
        cost = trade.price * trade.volume
        user_prefs.available_funds -= cost

    trade.closed = True
    trade.profit = profit if trade.action == 'buy' else -cost
    trade.save()
    user_prefs.save()

    return redirect('market_insights')


import requests


from decimal import Decimal

def get_live_bid_ask():
    url = "https://api.twelvedata.com/quote"
    params = {"symbol": "EUR/USD", "apikey": "48c496e7db274bcfb713f0cd8897cd56"}
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if 'bid' in data and 'ask' in data:
            return Decimal(data['bid']), Decimal(data['ask'])

        # Fallback: simulate bid/ask from close
        if 'close' in data:
            close = Decimal(data['close'])
            return close - Decimal('0.0002'), close + Decimal('0.0002')
    except Exception as e:
        print("❌ get_live_bid_ask error:", e)

    return None, None
