from prices import get_current_price, validate_ticker
from stocks import get_or_create_stock


def get_user_holding(conn, user_id, stock_id):
    """
    Calculate how many shares a user currently owns.

    BUY increases holdings.
    SELL decreases holdings.
    """

    with conn.cursor() as cur:

        cur.execute("""
            SELECT COALESCE(
                SUM(
                    CASE
                        WHEN transaction_type = 'BUY'
                            THEN quantity

                        WHEN transaction_type = 'SELL'
                            THEN -quantity
                    END
                ),
                0
            )
            FROM transactions
            WHERE user_id = %s
              AND stock_id = %s;
        """, (
            user_id,
            stock_id
        ))

        holding = cur.fetchone()[0]

    return int(holding)


def get_user_transactions(conn, user_id):
    """
    Get all transactions belonging to a user.
    """

    with conn.cursor() as cur:

        cur.execute("""
            SELECT
                t.id,
                s.ticker,
                s.company_name,
                t.transaction_type,
                t.quantity,
                t.price,
                t.transaction_date
            FROM transactions t
            JOIN stocks s
                ON t.stock_id = s.id
            WHERE t.user_id = %s
            ORDER BY
                t.transaction_date DESC,
                t.id DESC;
        """, (
            user_id,
        ))

        return cur.fetchall()


def buy_stock(conn, user_id):
    """
    Allow a user to buy a stock by entering its ticker.
    """

    ticker_input = input(
        "\nEnter stock ticker (0 to cancel): "
    ).strip().upper()

    if ticker_input == "0":

        print("Purchase cancelled.")
        return

    print(f"\nChecking ticker {ticker_input}...")

    stock_info = validate_ticker(
        ticker_input
    )

    if stock_info is None:

        print(
            f"\n{ticker_input} could not be "
            f"recognised by Yahoo Finance."
        )

        return

    print(
        f"Found: {stock_info['company_name']}"
    )

    print(
        f"Exchange: {stock_info['exchange']}"
    )

    selected_stock = get_or_create_stock(
        conn,
        stock_info["ticker"],
        stock_info["company_name"],
        stock_info["exchange"],
        stock_info["yahoo_ticker"]
    )

    if selected_stock is None:

        print("Could not create/find stock.")
        return

    (
        stock_id,
        ticker,
        company_name,
        exchange,
        yahoo_ticker
    ) = selected_stock

    print(
        f"\nSelected: {company_name} "
        f"({ticker})"
    )

    print("Getting current price...")

    current_price = get_current_price(
        yahoo_ticker
    )

    if current_price is None:

        print(
            "Could not retrieve the current price."
        )

        return

    print(
        f"Current price: "
        f"₹{current_price:,.2f}"
    )

    quantity_input = input(
        "\nEnter quantity to buy (0 to cancel): "
    ).strip()

    if quantity_input == "0":

        print("Purchase cancelled.")
        return

    try:

        quantity = int(quantity_input)

        if quantity <= 0:

            print(
                "Quantity must be greater than zero."
            )

            return

    except ValueError:

        print("Invalid quantity.")
        return

    transaction_value = (
        current_price * quantity
    )

    print("\nTransaction summary")
    print("-" * 40)

    print(f"Stock:       {company_name}")
    print(f"Ticker:      {ticker}")
    print(f"Action:      BUY")
    print(f"Quantity:    {quantity}")
    print(f"Price:       ₹{current_price:,.2f}")
    print(
        f"Total value: "
        f"₹{transaction_value:,.2f}"
    )

    confirmation = input(
        "\nConfirm transaction? (Y/N): "
    ).strip().upper()

    if confirmation != "Y":

        print("Transaction cancelled.")
        return

    try:

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
                VALUES
                (
                    %s,
                    %s,
                    'BUY',
                    %s,
                    %s,
                    CURRENT_DATE
                );
            """, (
                user_id,
                stock_id,
                quantity,
                current_price
            ))

        conn.commit()

        print(
            "\nPurchase successfully recorded!"
        )

    except Exception as e:

        conn.rollback()

        print("\nTransaction failed:")
        print(e)


def sell_stock(conn, user_id):
    """
    Allow a user to sell a stock they currently own.
    """

    # Get stocks that this user has actually
    # transacted in.
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

        stocks = cur.fetchall()

    owned_stocks = []

    for stock in stocks:

        stock_id = stock[0]

        holding = get_user_holding(
            conn,
            user_id,
            stock_id
        )

        if holding > 0:

            owned_stocks.append(
                (stock, holding)
            )

    if not owned_stocks:

        print(
            "\nYou don't currently own any stocks."
        )

        return

    print("\nYour holdings:")
    print("-" * 75)

    for stock, holding in owned_stocks:

        (
            stock_id,
            ticker,
            company_name,
            exchange,
            yahoo_ticker
        ) = stock

        print(
            f"{stock_id}. "
            f"{ticker:<15} "
            f"{company_name:<35} "
            f"{holding} shares"
        )

    try:

        stock_id = int(
            input(
                "\nEnter stock ID (0 to cancel): "
            ).strip()
        )

    except ValueError:

        print("Invalid stock ID.")
        return

    if stock_id == 0:

        print("Sale cancelled.")
        return

    selected = None

    for stock, holding in owned_stocks:

        if stock[0] == stock_id:

            selected = (
                stock,
                holding
            )

            break

    if selected is None:

        print(
            "You don't own that stock."
        )

        return

    stock, current_holding = selected

    (
        _,
        ticker,
        company_name,
        exchange,
        yahoo_ticker
    ) = stock

    print(
        f"\nSelected: "
        f"{company_name} ({ticker})"
    )

    print(
        f"You currently own: "
        f"{current_holding} shares"
    )

    if not yahoo_ticker:

        print(
            "There is no Yahoo Finance ticker "
            "available for this stock."
        )

        return

    print("Getting current price...")

    current_price = get_current_price(
        yahoo_ticker
    )

    if current_price is None:

        print(
            "Could not retrieve the current price."
        )

        return

    print(
        f"Current price: "
        f"₹{current_price:,.2f}"
    )

    try:

        quantity = int(
            input(
                "\nEnter quantity to sell "
                "(0 to cancel): "
            ).strip()
        )

        if quantity == 0:

            print("Sale cancelled.")
            return

        if quantity <= 0:

            print(
                "Quantity must be greater than zero."
            )

            return

    except ValueError:

        print("Invalid quantity.")
        return

    if quantity > current_holding:

        print(
            f"\nCannot sell {quantity} shares."
        )

        print(
            f"You only own "
            f"{current_holding} shares."
        )

        return

    transaction_value = (
        current_price * quantity
    )

    print("\nTransaction summary")
    print("-" * 40)

    print(f"Stock:       {company_name}")
    print(f"Ticker:      {ticker}")
    print(f"Action:      SELL")
    print(f"Quantity:    {quantity}")
    print(f"Price:       ₹{current_price:,.2f}")
    print(
        f"Total value: "
        f"₹{transaction_value:,.2f}"
    )

    confirmation = input(
        "\nConfirm transaction? (Y/N): "
    ).strip().upper()

    if confirmation != "Y":

        print("Transaction cancelled.")
        return

    try:

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
                VALUES
                (
                    %s,
                    %s,
                    'SELL',
                    %s,
                    %s,
                    CURRENT_DATE
                );
            """, (
                user_id,
                stock_id,
                quantity,
                current_price
            ))

        conn.commit()

        print(
            "\nSale successfully recorded!"
        )

    except Exception as e:

        conn.rollback()

        print("\nTransaction failed:")
        print(e)