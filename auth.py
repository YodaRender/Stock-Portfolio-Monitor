def login(conn):
    """Authenticate a user and return their user ID."""

    email = input("Email: ").strip()
    password = input("Password: ").strip()

    with conn.cursor() as cur:

        cur.execute("""
            SELECT id, name, password_hash
            FROM users
            WHERE email = %s;
        """, (email,))

        user = cur.fetchone()

    if user is None:
        print("\nInvalid email or password.")
        return None

    user_id, name, stored_password = user

    if password != stored_password:
        print("\nInvalid email or password.")
        return None

    print(f"\nWelcome, {name}!")

    return user_id


def register(conn):
    """Create a new user account."""

    print("\n========== CREATE ACCOUNT ==========")

    name = input("Name: ").strip()
    email = input("Email: ").strip()
    password = input("Password: ").strip()

    if not name or not email or not password:
        print("\nAll fields are required.")
        return None

    # Check whether email already exists
    with conn.cursor() as cur:

        cur.execute("""
            SELECT id
            FROM users
            WHERE email = %s;
        """, (email,))

        existing_user = cur.fetchone()

    if existing_user is not None:
        print("\nAn account with this email already exists.")
        return None

    try:

        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO users
                (
                    name,
                    email,
                    password_hash
                )
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (
                name,
                email,
                password
            ))

            user_id = cur.fetchone()[0]

        conn.commit()

        print("\nAccount created successfully!")
        print(f"Your user ID is: {user_id}")

        return user_id

    except Exception as e:

        conn.rollback()

        print("\nCould not create account:")
        print(e)

        return None