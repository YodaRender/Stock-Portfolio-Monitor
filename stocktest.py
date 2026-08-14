import psycopg2
import yfinance as yf


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "portfolio_tracker",
    "user": "postgres",
    "password": "Thejas12*"
}


def get_current_price(ticker):
    """Get the latest available price from Yahoo Finance."""

    stock = yf.Ticker(ticker)

    try:
        price = stock.fast_info["last_price"]

        if price is None:
            return None

        return float(price)

    except Exception:
        return None


def get_user_stocks(conn):
    """Get all stocks currently supported by our application."""

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, ticker, company_name, exchange
            FROM stocks
            ORDER BY company_name;
        """)

        return cur.fetchall()


def get_user_holding(conn, user_id, stock_id):
    """Return the number of shares currently owned by the user."""

    with conn.cursor() as cur:

        cur.execute("""
            SELECT COALESCE(
                SUM(
                    CASE
                        WHEN transaction_type = 'BUY' THEN quantity
                        WHEN transaction_type = 'SELL' THEN -quantity
                    END
                ),
                0
            )
            FROM transactions
            WHERE user_id = %s
              AND stock_id = %s;
        """, (user_id, stock_id))

        holding = cur.fetchone()[0]

        return int(holding)


def buy_sell_stock(user_id):

    # Connect to PostgreSQL
    conn = psycopg2.connect(**DB_CONFIG)

    try:

        # --------------------------------
        # 1. Show available stocks
        # --------------------------------

        stocks = get_user_stocks(conn)

        if not stocks:
            print("No stocks are currently available.")
            return

        print("\nAvailable stocks:")
        print("-" * 60)

        for stock in stocks:
            stock_id, ticker, company_name, exchange = stock

            print(
                f"{stock_id}. {ticker:<15} "
                f"{company_name} ({exchange})"
            )

        # --------------------------------
        # 2. User chooses stock
        # --------------------------------

        try:
            stock_id = int(input("\nEnter stock ID: "))
        except ValueError:
            print("Invalid stock ID.")
            return

        selected_stock = None

        for stock in stocks:
            if stock[0] == stock_id:
                selected_stock = stock
                break

        if selected_stock is None:
            print("Invalid stock selection.")
            return

        _, ticker, company_name, exchange = selected_stock

        print(f"\nSelected: {company_name} ({ticker})")

        # --------------------------------
        # 3. Get current market price
        # --------------------------------

        print("Getting current price...")

        current_price = get_current_price(ticker)

        if current_price is None:
            print("Could not retrieve the current price.")
            return

        print(f"Current price: ₹{current_price:,.2f}")

        # --------------------------------
        # 4. BUY or SELL
        # --------------------------------

        action = input("\nDo you want to BUY or SELL? ").upper()

        if action not in ("BUY", "SELL"):
            print("Invalid action. Please enter BUY or SELL.")
            return

        # --------------------------------
        # 5. Quantity
        # --------------------------------

        try:
            quantity = int(input("Enter quantity: "))

            if quantity <= 0:
                print("Quantity must be greater than zero.")
                return

        except ValueError:
            print("Invalid quantity.")
            return

        # --------------------------------
        # 6. If SELL, check ownership
        # --------------------------------

        if action == "SELL":

            current_holding = get_user_holding(
                conn,
                user_id,
                stock_id
            )

            print(f"\nYou currently own {current_holding} shares of {ticker}.")

            if current_holding == 0:
                print("You do not own this stock.")
                return

            if quantity > current_holding:
                print(
                    f"Cannot sell {quantity} shares.\n"
                    f"You only own {current_holding} shares."
                )
                return

        # --------------------------------
        # 7. Calculate transaction value
        # --------------------------------

        transaction_value = current_price * quantity

        print("\nTransaction summary")
        print("-" * 40)
        print(f"Stock:       {company_name}")
        print(f"Ticker:      {ticker}")
        print(f"Action:      {action}")
        print(f"Quantity:    {quantity}")
        print(f"Price:       ₹{current_price:,.2f}")
        print(f"Total value: ₹{transaction_value:,.2f}")

        # --------------------------------
        # 8. Confirm
        # --------------------------------

        confirmation = input("\nConfirm transaction? (Y/N): ").upper()

        if confirmation != "Y":
            print("Transaction cancelled.")
            return

        # --------------------------------
        # 9. Insert transaction
        # --------------------------------

        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO transactions
                (
                    user_id,
                    stock_id,
                    transaction_type,
                    quantity,
                    price,
                    transaction_date
                )
                VALUES (%s, %s, %s, %s, %s, CURRENT_DATE);
            """, (
                user_id,
                stock_id,
                action,
                quantity,
                current_price
            ))

        conn.commit()

        print("\nTransaction successfully recorded!")

    except Exception as e:

        conn.rollback()

        print("Transaction failed:")
        print(e)

    finally:
        conn.close()

buy_sell_stock(1)