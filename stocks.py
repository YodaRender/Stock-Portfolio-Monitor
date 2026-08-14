def get_all_stocks(conn):
    """
    Return all stocks stored in the database.
    """

    with conn.cursor() as cur:

        cur.execute("""
            SELECT
                id,
                ticker,
                company_name,
                exchange,
                yahoo_ticker
            FROM stocks
            ORDER BY company_name;
        """)

        return cur.fetchall()


def get_stock_by_ticker(conn, ticker):
    """
    Find a stock using its application ticker.
    """

    with conn.cursor() as cur:

        cur.execute("""
            SELECT
                id,
                ticker,
                company_name,
                exchange,
                yahoo_ticker
            FROM stocks
            WHERE ticker = %s;
        """, (ticker,))

        return cur.fetchone()


def get_or_create_stock(
    conn,
    ticker,
    company_name=None,
    exchange=None,
    yahoo_ticker=None
):
    """
    Find an existing stock or create it.

    ticker:
        Application/broker ticker, e.g. DRREDDY

    yahoo_ticker:
        Yahoo ticker, e.g. DRREDDY.NS
    """

    ticker = ticker.strip().upper()

    existing_stock = get_stock_by_ticker(
        conn,
        ticker
    )

    if existing_stock is not None:

        stock_id, db_ticker, db_company, db_exchange, db_yahoo_ticker = existing_stock

        # If we previously didn't know the Yahoo ticker,
        # but now we do, update it.
        if yahoo_ticker and not db_yahoo_ticker:

            with conn.cursor() as cur:

                cur.execute("""
                    UPDATE stocks
                    SET
                        yahoo_ticker = %s,
                        company_name = COALESCE(%s, company_name),
                        exchange = COALESCE(%s, exchange)
                    WHERE id = %s;
                """, (
                    yahoo_ticker,
                    company_name,
                    exchange,
                    stock_id
                ))

            conn.commit()

            return (
                stock_id,
                db_ticker,
                company_name or db_company,
                exchange or db_exchange,
                yahoo_ticker
            )

        return existing_stock

    # Stock doesn't exist yet.
    with conn.cursor() as cur:

        cur.execute("""
            INSERT INTO stocks
            (
                ticker,
                company_name,
                exchange,
                yahoo_ticker
            )
            VALUES (%s, %s, %s, %s)
            RETURNING
                id,
                ticker,
                company_name,
                exchange,
                yahoo_ticker;
        """, (
            ticker,
            company_name,
            exchange,
            yahoo_ticker
        ))

        stock = cur.fetchone()

    conn.commit()

    return stock