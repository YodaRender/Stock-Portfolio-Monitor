from database import get_connection
from auth import login, register
from portfolio import display_portfolio
from import_transactions import import_transactions
from transactions import (
    buy_stock,
    sell_stock,
    get_user_transactions
)


def display_transactions(conn, user_id):

    transactions = get_user_transactions(
        conn,
        user_id
    )

    if not transactions:

        print("\nYou have no transactions.")
        return

    print("\n")
    print("=" * 90)
    print("                         TRANSACTION HISTORY")
    print("=" * 90)

    for transaction in transactions:

        (
            transaction_id,
            ticker,
            company_name,
            transaction_type,
            quantity,
            price,
            transaction_date
        ) = transaction

        total_value = quantity * price

        print(
            f"{transaction_date} | "
            f"{transaction_type:<4} | "
            f"{ticker:<12} | "
            f"{quantity:<5} | "
            f"₹{price:,.2f} | "
            f"₹{total_value:,.2f}"
        )

    print("=" * 90)


def show_menu():

    print("\n")
    print("=" * 40)
    print("          PORTFOLIO TRACKER")
    print("=" * 40)

    print("1. View my portfolio")
    print("2. Buy stock")
    print("3. Sell stock")
    print("4. View transaction history")
    print("5. Import transaction record(CSV)")
    print("6. Logout")

    print("=" * 40)


def main():

    conn = get_connection()

    try:

        # --------------------------------
        # LOGIN / REGISTER
        # --------------------------------

        while True:

            print("\n")
            print("=" * 40)
            print("          PORTFOLIO TRACKER")
            print("=" * 40)

            print("1. Login")
            print("2. Create account")
            print("3. Exit")

            print("=" * 40)

            choice = input("Enter your choice: ").strip()

            if choice == "1":

                user_id = login(conn)

                if user_id is not None:
                    break

            elif choice == "2":

                register(conn)

            elif choice == "3":

                print("\nGoodbye!")
                return

            else:

                print("\nInvalid choice.")

        # --------------------------------
        # USER MENU
        # --------------------------------

        while True:

            show_menu()

            choice = input(
                "Enter your choice: "
            ).strip()

            if choice == "1":

                display_portfolio(
                    conn,
                    user_id
                )

            elif choice == "2":

                buy_stock(
                    conn,
                    user_id
                )

            elif choice == "3":

                sell_stock(
                    conn,
                    user_id
                )

            elif choice == "4":

                display_transactions(
                    conn,
                    user_id
                )

            elif choice == "5":

                file_path = input(
                    "Enter CSV file path (0 to cancel): "
                ).strip()

                if file_path == "0":
                    print("Import cancelled.")
                    continue

                import_transactions(
                    conn,
                    user_id,
                    file_path
                )

            elif choice == "6":

                print("\nLogged out successfully.")
                break

            else:

                print(
                    "\nInvalid choice. "
                    "Please choose 1-6."
                )

    except Exception as e:

        print("\nApplication error:")
        print(e)

    finally:

        conn.close()


if __name__ == "__main__":
    main()