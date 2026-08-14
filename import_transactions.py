import csv
from datetime import datetime

from prices import validate_ticker
from stocks import get_stock_by_ticker, get_or_create_stock


def import_transactions(conn, user_id, csv_file):
    """
    Import historical transactions from a CSV.

    Required CSV columns:

        ticker
        transaction_type
        quantity
        price
        transaction_date

    Extra columns are ignored.

    Yahoo Finance is used to resolve tickers where possible,
    but a historical transaction is NOT rejected merely
    because Yahoo Finance cannot currently find the ticker.
    """

    try:

        # =================================================
        # 1. READ CSV
        # =================================================

        with open(
            csv_file,
            "r",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            reader = csv.DictReader(file)

            required_columns = {
                "ticker",
                "transaction_type",
                "quantity",
                "price",
                "transaction_date"
            }

            if not reader.fieldnames:

                print("\nCSV has no header row.")
                return

            # Make column names case-insensitive.
            field_map = {
                column.strip().lower(): column
                for column in reader.fieldnames
            }

            missing = (
                required_columns
                - set(field_map.keys())
            )

            if missing:

                print(
                    "\nCSV is missing required columns:"
                )

                for column in sorted(missing):

                    print(f"- {column}")

                return

            rows = list(reader)

        if not rows:

            print("\nCSV file is empty.")
            return

        # =================================================
        # 2. PARSE AND VALIDATE BASIC DATA
        # =================================================

        parsed_rows = []

        for row_number, row in enumerate(
            rows,
            start=2
        ):

            ticker = (
                row[field_map["ticker"]]
                .strip()
                .upper()
            )

            transaction_type = (
                row[field_map["transaction_type"]]
                .strip()
                .upper()
            )

            try:

                quantity = int(
                    row[field_map["quantity"]]
                    .strip()
                )

                price = float(
                    row[field_map["price"]]
                    .strip()
                )

                transaction_date = datetime.strptime(
                    row[field_map["transaction_date"]]
                    .strip(),
                    "%Y-%m-%d"
                ).date()

            except (ValueError, TypeError):

                print(
                    f"\nInvalid data on CSV row "
                    f"{row_number}."
                )

                return

            if not ticker:

                print(
                    f"\nEmpty ticker on row "
                    f"{row_number}."
                )

                return

            if transaction_type not in (
                "BUY",
                "SELL"
            ):

                print(
                    f"\nInvalid transaction type "
                    f"on row {row_number}: "
                    f"{transaction_type}"
                )

                return

            if quantity <= 0:

                print(
                    f"\nQuantity must be greater "
                    f"than zero on row "
                    f"{row_number}."
                )

                return

            if price <= 0:

                print(
                    f"\nPrice must be greater "
                    f"than zero on row "
                    f"{row_number}."
                )

                return

            parsed_rows.append({
                "row_number": row_number,
                "ticker": ticker,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "price": price,
                "transaction_date": transaction_date
            })

        # =================================================
        # 3. SORT TRANSACTIONS
        # =================================================
        #
        # For the same date, BUY transactions are
        # processed before SELL transactions.
        #
        # This prevents an otherwise valid same-day
        # BUY → SELL sequence from failing simply because
        # the CSV listed the SELL first.

        parsed_rows.sort(
            key=lambda row: (
                row["transaction_date"],
                0 if row["transaction_type"] == "BUY" else 1
            )
        )

        # =================================================
        # 4. RESOLVE UNIQUE TICKERS
        # =================================================

        ticker_cache = {}

        unresolved_tickers = set()

        for row in parsed_rows:

            ticker = row["ticker"]

            if ticker in ticker_cache:
                continue

            print(
                f"\nResolving ticker {ticker}..."
            )

            stock_info = validate_ticker(
                ticker
            )

            ticker_cache[ticker] = stock_info

            if stock_info is None:

                unresolved_tickers.add(
                    ticker
                )

                print(
                    f"Yahoo Finance could not "
                    f"resolve {ticker}."
                )

        # =================================================
        # 5. GET OR CREATE STOCKS
        # =================================================

        stock_cache = {}

        for ticker, stock_info in ticker_cache.items():

            existing_stock = get_stock_by_ticker(
                conn,
                ticker
            )

            if existing_stock is not None:

                stock_cache[ticker] = existing_stock

                # If Yahoo has now resolved a ticker
                # that previously had no Yahoo ticker,
                # update it.

                if (
                    stock_info is not None
                    and not existing_stock[4]
                ):

                    with conn.cursor() as cur:

                        cur.execute("""
                            UPDATE stocks
                            SET
                                yahoo_ticker = %s,
                                company_name = %s,
                                exchange = %s
                            WHERE id = %s;
                        """, (
                            stock_info["yahoo_ticker"],
                            stock_info["company_name"],
                            stock_info["exchange"],
                            existing_stock[0]
                        ))

                    conn.commit()

                    stock_cache[ticker] = (
                        existing_stock[0],
                        existing_stock[1],
                        stock_info["company_name"],
                        stock_info["exchange"],
                        stock_info["yahoo_ticker"]
                    )

                continue

            # ---------------------------------------------
            # Yahoo recognized ticker
            # ---------------------------------------------

            if stock_info is not None:

                stock_cache[ticker] = get_or_create_stock(
                    conn,
                    ticker,
                    stock_info["company_name"],
                    stock_info["exchange"],
                    stock_info["yahoo_ticker"]
                )

            # ---------------------------------------------
            # Yahoo could not recognize ticker
            # ---------------------------------------------

            else:

                stock_cache[ticker] = get_or_create_stock(
                    conn,
                    ticker,
                    ticker,
                    None,
                    None
                )

        # =================================================
        # 6. GET EXISTING USER HOLDINGS
        # =================================================

        holdings = {}

        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    stock_id,
                    COALESCE(
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
                GROUP BY stock_id;
            """, (
                user_id,
            ))

            existing_holdings = cur.fetchall()

        for stock_id, quantity in existing_holdings:

            holdings[stock_id] = int(quantity)

        # =================================================
        # 7. VALIDATE HOLDINGS
        # =================================================

        for row in parsed_rows:

            ticker = row["ticker"]

            stock = stock_cache[ticker]

            stock_id = stock[0]

            quantity = row["quantity"]

            current_holding = holdings.get(
                stock_id,
                0
            )

            if row["transaction_type"] == "BUY":

                holdings[stock_id] = (
                    current_holding + quantity
                )

            else:

                if quantity > current_holding:

                    print(
                        "\nCannot import CSV."
                    )

                    print(
                        f"Row {row['row_number']}: "
                        f"attempting to sell "
                        f"{quantity} shares of "
                        f"{ticker}."
                    )

                    print(
                        f"Available shares at that "
                        f"point: {current_holding}"
                    )

                    print(
                        "\nNo transactions have "
                        "been inserted."
                    )

                    return

                holdings[stock_id] = (
                    current_holding - quantity
                )

        # =================================================
        # 8. INSERT EVERYTHING
        # =================================================

        with conn.cursor() as cur:

            for row in parsed_rows:

                stock_id = stock_cache[
                    row["ticker"]
                ][0]

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
                        %s,
                        %s,
                        %s,
                        %s
                    );
                """, (
                    user_id,
                    stock_id,
                    row["transaction_type"],
                    row["quantity"],
                    row["price"],
                    row["transaction_date"]
                ))

        conn.commit()

        # =================================================
        # 9. REPORT RESULT
        # =================================================

        print(
            f"\nSuccessfully imported "
            f"{len(parsed_rows)} transactions."
        )

        if unresolved_tickers:

            print(
                "\nThe following historical tickers "
                "could not be resolved by Yahoo Finance:"
            )

            for ticker in sorted(
                unresolved_tickers
            ):

                print(
                    f"  - {ticker}"
                )

            print(
                "\nTheir transactions were still "
                "imported. Current prices may not "
                "be available for these stocks."
            )

    except Exception as e:

        conn.rollback()

        print(
            "\nImport failed."
        )

        print(e)