from datetime import timedelta
from django.utils import timezone
from django.utils.timezone import is_naive, make_aware
import pandas as pd
import MetaTrader5 as mt5
from .models import MT5Candle

def fetch_and_save_mt5_data(symbol="EURUSD"):
    try:
        MT5_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
        if not mt5.initialize(path=MT5_PATH):
            print(f"❌ MT5 init failed: {mt5.last_error()}")
            return

        # Step 1: Get last saved candle timestamp
        last_record = MT5Candle.objects.filter(symbol=symbol).order_by('-time').first()
        if last_record:
            from_date = last_record.time + timedelta(minutes=15)
        else:
            # Start from 30 days ago if no data exists
            from_date = timezone.now() - timedelta(days=30)

        to_date = timezone.now()

        if from_date >= to_date:
            mt5.shutdown()
            print("ℹ️ No new data to fetch.")
            return

        print(f"⏳ Fetching from {from_date} to {to_date}...")

        from_naive = from_date.replace(tzinfo=None)
        to_naive = to_date.replace(tzinfo=None)

        # Step 2: Fetch all candles between from_date and now
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, from_naive, to_naive)
        mt5.shutdown()

        if rates is None or len(rates) == 0:
            print("ℹ️ No new candles found.")
            return

        # Step 3: Format and save each new candle
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "tick_volume"]]

        saved = 0
        for _, row in df.iterrows():
            ts = row["time"]
            if is_naive(ts):
                ts = make_aware(ts)

            obj, created = MT5Candle.objects.get_or_create(
                symbol=symbol,
                time=ts,
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

        print(f"✅ Done. Saved {saved} new candles for {symbol}.")
    except Exception as e:
        print("❌ Error fetching MT5 data:", str(e))
