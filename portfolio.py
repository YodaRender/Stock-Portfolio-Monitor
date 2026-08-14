from transactions import get_user_holding
from prices import get_current_price


def get_user_stocks(conn, user_id):
    """
    Get stocks that the user has transactions for.
    """

    with conn.cursor() as cur:

        cur.execute("""
            SELECT DISTINCT
                s.id,
                s.ticker,
                s.company_name,
                s.exchange,
                s.yahoo_ticker
            FROM stocks s
            JOIN transactions t
                ON s.id = t.stock_id
            WHERE t.user_id = %s
            ORDER BY s.company_name;
        """, (
            user_id,
        ))

        return cur.fetchall()


def get_user_portfolio(conn, user_id):
    """
    Return all stocks currently owned by the user,
    along with quantity and current price.
    """

    portfolio = []

    with conn.cursor() as cur:

        cur.execute("""
            SELECT DISTINCT
                s.id,
                s.ticker,
                s.company_name,
                s.exchange,
                s.yahoo_ticker
            FROM stocks s
            JOIN transactions t
                ON t.stock_id = s.id
            WHERE t.user_id = %s
            ORDER BY s.ticker;
        """, (user_id,))

        stocks = cur.fetchall()

    for stock in stocks:

        (
            stock_id,
            ticker,
            company_name,
            exchange,
            yahoo_ticker
        ) = stock

        quantity = get_user_holding(
            conn,
            user_id,
            stock_id
        )

        if quantity <= 0:
            continue

        # -----------------------------------------
        # No Yahoo ticker
        # -----------------------------------------

        if not yahoo_ticker:

            portfolio.append({
                "stock_id": stock_id,
                "ticker": ticker,
                "company_name": company_name,
                "quantity": quantity,
                "current_price": None,
                "current_value": None
            })

            continue

        # -----------------------------------------
        # Get current Yahoo price
        # -----------------------------------------

        current_price = get_current_price(
            yahoo_ticker
        )

        if current_price is None:

            portfolio.append({
                "stock_id": stock_id,
                "ticker": ticker,
                "company_name": company_name,
                "quantity": quantity,
                "current_price": None,
                "current_value": None
            })

            continue

        current_value = quantity * current_price

        portfolio.append({
            "stock_id": stock_id,
            "ticker": ticker,
            "company_name": company_name,
            "quantity": quantity,
            "current_price": current_price,
            "current_value": current_value
        })

    return portfolio


def display_portfolio(conn, user_id):

    portfolio = get_user_portfolio(
        conn,
        user_id
    )

    if not portfolio:

        print("\nYour portfolio is empty.")
        return

    print("\n")
    print("=" * 90)
    print("                         MY PORTFOLIO")
    print("=" * 90)

    print(
        f"{'Ticker':<15}"
        f"{'Quantity':<12}"
        f"{'Current Price':<20}"
        f"{'Current Value':<20}"
    )

    print("-" * 90)

    total_value = 0
    unavailable_count = 0

    for stock in portfolio:

        ticker = stock["ticker"]
        quantity = stock["quantity"]
        current_price = stock["current_price"]
        current_value = stock["current_value"]

        if current_price is None:

            price_display = "Unavailable"
            value_display = "Unavailable"

            unavailable_count += 1

        else:

            price_display = f"₹{current_price:,.2f}"
            value_display = f"₹{current_value:,.2f}"

            total_value += current_value

        print(
            f"{ticker:<15}"
            f"{quantity:<12}"
            f"{price_display:<20}"
            f"{value_display:<20}"
        )

    print("-" * 90)

    print(
        f"{'TOTAL':<47}"
        f"₹{total_value:,.2f}"
    )

    if unavailable_count > 0:

        print(
            f"\nNote: Current prices are unavailable "
            f"for {unavailable_count} stock(s)."
        )

        print(
            "Their values are therefore excluded "
            "from the portfolio total."
        )

    print("=" * 90)