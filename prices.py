import yfinance as yf


def validate_ticker(ticker):
    """
    Validate an Indian stock ticker using Yahoo Finance.

    Accepts:
        TCS
        TCS.NS
        TCS.BO

    If no exchange suffix is supplied:
        NSE is tried first
        BSE is tried second

    Returns:
        {
            "ticker": original ticker,
            "yahoo_ticker": Yahoo Finance ticker,
            "company_name": company name,
            "exchange": exchange
        }

    Returns None if Yahoo Finance cannot find the ticker.
    """

    ticker = ticker.strip().upper()

    if not ticker:
        return None

    # If exchange is already specified
    if ticker.endswith(".NS") or ticker.endswith(".BO"):

        candidates = [ticker]
        original_ticker = ticker.rsplit(".", 1)[0]

    else:

        original_ticker = ticker

        candidates = [
            f"{ticker}.NS",
            f"{ticker}.BO"
        ]

    for yahoo_ticker in candidates:

        print(f"Checking ticker {yahoo_ticker}...")

        try:

            stock = yf.Ticker(yahoo_ticker)

            history = stock.history(
                period="5d"
            )

            if history.empty:
                continue

            # Company information isn't always available,
            # so don't let failure here invalidate the ticker.
            try:
                info = stock.info
            except Exception:
                info = {}

            company_name = (
                info.get("longName")
                or info.get("shortName")
                or original_ticker
            )

            if yahoo_ticker.endswith(".NS"):
                exchange = "NSE"

            elif yahoo_ticker.endswith(".BO"):
                exchange = "BSE"

            else:
                exchange = info.get("exchange") or ""

            return {
                "ticker": original_ticker,
                "yahoo_ticker": yahoo_ticker,
                "company_name": company_name,
                "exchange": exchange
            }

        except Exception:
            continue

    print(
        f"Yahoo Finance could not resolve {original_ticker}."
    )

    return None


def get_current_price(ticker):
    """
    Get the latest available stock price from Yahoo Finance.

    Accepts:
        TCS
        TCS.NS
        TCS.BO

    Returns:
        float
        or None if no price is available.
    """

    if not ticker:
        return None

    ticker = ticker.strip().upper()

    print(f"Getting current price for {ticker}...")

    try:

        stock = yf.Ticker(ticker)

        # -----------------------------------------
        # 1. Try fast_info
        # -----------------------------------------

        try:

            price = stock.fast_info.get("last_price")

            if price is not None:

                price = float(price)

                if not price != price:  # check for NaN
                    return price

        except Exception as e:

            print(
                f"fast_info failed for {ticker}: {e}"
            )

        # -----------------------------------------
        # 2. Fall back to recent history
        # -----------------------------------------

        history = stock.history(
            period="5d"
        )

        if history.empty:

            print(
                f"No historical price data for {ticker}."
            )

            return None

        # Remove rows where Close is NaN
        closes = history["Close"].dropna()

        if closes.empty:

            print(
                f"No valid closing prices for {ticker}."
            )

            return None

        # Last valid closing price
        price = float(closes.iloc[-1])

        print(
            f"Using latest available price: ₹{price:,.2f}"
        )

        return price

    except Exception as e:

        print(
            f"Could not get price for {ticker}: {e}"
        )

        return None