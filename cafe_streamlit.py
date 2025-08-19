# streamlit_app.py
import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# ----------------------------
# Basic Page Setup
# ----------------------------
st.set_page_config(page_title="Cafe Central", page_icon="☕", layout="wide")
st.title("☕ Cafe Central Management System")

# ----------------------------
# Session State Initialization
# ----------------------------
DEFAULT_STATE = {
    "customer_id": None,
    "order": [],   # list of tuples: (item_id, qty, subtotal)
}
for k, v in DEFAULT_STATE.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ----------------------------
# Database Setup
# ----------------------------
conn = sqlite3.connect("cafe_central.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    upi_number TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    total_price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES menu(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    review TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES menu(id) ON DELETE CASCADE
);
""")
conn.commit()

# Small helpers
def df_from_rows(rows, cols):
    return pd.DataFrame(rows, columns=cols)

def money(x):
    return f"₹{x:.2f}"

# ----------------------------
# Role Picker
# ----------------------------
role = st.sidebar.radio("Login as:", ["Customer", "Admin"])

# =========================================================
# Admin Section
# =========================================================
if role == "Admin":
    st.header("🔑 Admin Dashboard")
    choice = st.sidebar.selectbox("Choose an action", [
        "View Customers",
        "View Orders",
        "Manage Menu",
        "View Sales Report"
    ])

    # ---- View Customers ----
    if choice == "View Customers":
        st.subheader("👥 Customers List")
        customers = cursor.execute("SELECT id, name, phone, email, created_at FROM customers").fetchall()
        if customers:
            df = df_from_rows(customers, ["Customer ID", "Name", "Phone", "Email", "Created At"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No customers found.")

    # ---- View Orders ----
    elif choice == "View Orders":
        st.subheader("🛒 Orders List")
        orders = cursor.execute("SELECT id, customer_id, date, upi_number FROM orders ORDER BY date DESC").fetchall()
        if orders:
            df = df_from_rows(orders, ["Order ID", "Customer ID", "Date", "UPI Number"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No orders placed yet.")

    # ---- Manage Menu (with Avg Rating) ----
    elif choice == "Manage Menu":
        st.subheader("📋 Manage Menu")
        menu_items = cursor.execute("SELECT id, name, category, price FROM menu ORDER BY id").fetchall()
        if menu_items:
            # Enrich with avg rating
            enriched = []
            for m in menu_items:
                ratings = cursor.execute("SELECT rating FROM reviews WHERE item_id = ?", (m[0],)).fetchall()
                avg = round(sum(r[0] for r in ratings) / len(ratings), 1) if ratings else None
                enriched.append([m[0], m[1], m[2], m[3], (f"{avg} ⭐" if avg is not None else "—")])
            df = df_from_rows(enriched, ["Item ID", "Name", "Category", "Price", "Avg Rating"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Menu is empty.")

        st.markdown("---")
        action = st.radio("Choose Action:", ["Add Item", "Remove Item", "Update Item"], horizontal=True)

        if action == "Add Item":
            with st.form("add_item_form"):
                name = st.text_input("Item Name")
                category = st.text_input("Category")
                price = st.number_input("Price", min_value=0.0, format="%.2f")
                submitted = st.form_submit_button("Add Item")
                if submitted:
                    if name and category:
                        cursor.execute("INSERT INTO menu (name, category, price) VALUES (?, ?, ?)",
                                       (name, category, price))
                        conn.commit()
                        st.success(f"Added '{name}' to the menu!")
                    else:
                        st.error("Please fill all fields.")

        elif action == "Remove Item":
            with st.form("remove_item_form"):
                item_id = st.number_input("Enter Item ID to remove", min_value=1, step=1)
                submitted = st.form_submit_button("Remove Item")
                if submitted:
                    cursor.execute("DELETE FROM menu WHERE id = ?", (item_id,))
                    conn.commit()
                    st.warning(f"Item with ID {item_id} removed (if it existed).")

        elif action == "Update Item":
            with st.form("load_item_form"):
                item_id = st.number_input("Enter Item ID to update", min_value=1, step=1)
                load = st.form_submit_button("Load Item")
            if load:
                item = cursor.execute("SELECT id, name, category, price FROM menu WHERE id = ?", (item_id,)).fetchone()
                if item:
                    with st.form("update_item_form"):
                        new_name = st.text_input("Item Name", item[1])
                        new_category = st.text_input("Category", item[2])
                        new_price = st.number_input("Price", value=float(item[3]), format="%.2f")
                        submitted = st.form_submit_button("Update Item")
                        if submitted:
                            cursor.execute("UPDATE menu SET name=?, category=?, price=? WHERE id=?",
                                           (new_name, new_category, new_price, item_id))
                            conn.commit()
                            st.success("Item updated successfully.")
                else:
                    st.error("Item not found.")

    # ---- Sales Reports ----
    elif choice == "View Sales Report":
        # Monthly
        st.subheader("📊 Monthly Sales Report")
        monthly = cursor.execute("""
            SELECT strftime('%Y-%m', o.date) AS ym, SUM(oi.total_price) AS total_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            GROUP BY ym
            ORDER BY ym
        """).fetchall()
        if monthly:
            dfm = df_from_rows(monthly, ["Month", "Total Sales"])
            st.dataframe(dfm, use_container_width=True)
            chart_dfm = dfm.set_index("Month")
            st.bar_chart(chart_dfm)
        else:
            st.info("No sales data available yet.")

        # Daily
        st.subheader("📅 Daily Sales Report")
        daily = cursor.execute("""
            SELECT strftime('%Y-%m-%d', o.date) AS day, SUM(oi.total_price) AS total_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            GROUP BY day
            ORDER BY day
        """).fetchall()
        if daily:
            dfd = df_from_rows(daily, ["Date", "Total Sales"])
            st.dataframe(dfd, use_container_width=True)
            chart_dfd = dfd.set_index("Date")
            st.bar_chart(chart_dfd)
        else:
            st.info("No daily sales data yet.")

# =========================================================
# Customer Section
# =========================================================
elif role == "Customer":
    st.header("👤 Customer Portal")

    # ---- New Registration ----
    st.subheader("🆕 New Customer Registration")
    with st.form("register_form"):
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
        register_btn = st.form_submit_button("Register")
        if register_btn:
            if name and phone and email:
                try:
                    cursor.execute("INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)",
                                   (name, phone, email))
                    conn.commit()
                    customer_id = cursor.lastrowid
                    st.success(f"Registered successfully! Your Customer ID is {customer_id}")
                except sqlite3.IntegrityError:
                    st.error("Email already exists. Try logging in or use another email.")
            else:
                st.error("Please fill all fields.")

    st.markdown("---")

    # ---- Existing Login ----
    st.subheader("🔑 Existing Customer Login")
    if st.session_state.customer_id is None:
        with st.form("login_form"):
            customer_id_input = st.number_input("Enter Customer ID", min_value=1, step=1)
            login_btn = st.form_submit_button("Login")
        if login_btn:
            customer = cursor.execute("SELECT id, name FROM customers WHERE id = ?",
                                      (customer_id_input,)).fetchone()
            if customer:
                st.session_state.customer_id = customer[0]
                st.success(f"Welcome back, {customer[1]}!")
            else:
                st.error("Invalid Customer ID.")

    # ---- Logged-in Area ----
    if st.session_state.customer_id is not None:
        customer = cursor.execute("SELECT id, name FROM customers WHERE id = ?",
                                  (st.session_state.customer_id,)).fetchone()
        if customer:
            st.success(f"Welcome back, {customer[1]}!")

        # Ensure order list exists
        if "order" not in st.session_state:
            st.session_state.order = []

        # -------- Menu + Cart Form --------
        menu_items = cursor.execute("SELECT id, name, category, price FROM menu ORDER BY id").fetchall()
        if menu_items:
            st.subheader("🍽️ Menu")
            with st.form("menu_form"):
                order_quantities = {}
                for item in menu_items:
                    order_quantities[item[0]] = st.number_input(
                        f"{item[1]} ({money(item[3])})", min_value=0, step=1, key=f"item_{item[0]}"
                    )
                submit_order = st.form_submit_button("Update Cart")

            # Build cart from selections
            st.session_state.order = []
            total_amount = 0.0
            summary_rows = []
            for item_id, qty in order_quantities.items():
                if qty > 0:
                    price, name = cursor.execute(
                        "SELECT price, name FROM menu WHERE id = ?", (item_id,)
                    ).fetchone()
                    subtotal = price * qty
                    st.session_state.order.append((item_id, qty, subtotal))
                    summary_rows.append([name, qty, money(subtotal)])
                    total_amount += subtotal

            if st.session_state.order:
                st.markdown("---")
                st.subheader("📝 Order Summary")
                st.dataframe(df_from_rows(summary_rows, ["Item", "Qty", "Subtotal"]),
                             use_container_width=True)
                st.write(f"**Total: {money(total_amount)}**")

                if st.button("Place Order"):
                    cursor.execute("INSERT INTO orders (customer_id, date) VALUES (?, ?)",
                                   (st.session_state.customer_id, datetime.now()))
                    new_order_id = cursor.lastrowid
                    for item_id, qty, subtotal in st.session_state.order:
                        cursor.execute(
                            "INSERT INTO order_items (order_id, item_id, quantity, total_price) VALUES (?, ?, ?, ?)",
                            (new_order_id, item_id, qty, subtotal)
                        )
                    conn.commit()
                    st.success(f"✅ Order placed successfully! Your Order ID is {new_order_id}")
                    st.session_state.order = []

            # -------- Ratings & Reviews --------
            st.markdown("---")
            st.subheader("⭐ Rate & Review Menu Items")
            for item in menu_items:
                with st.expander(f"{item[1]} ({money(item[3])})"):
                    st.caption(f"Category: {item[2]}")
                    revs = cursor.execute(
                        "SELECT rating, review, created_at FROM reviews WHERE item_id = ? ORDER BY created_at DESC",
                        (item[0],)
                    ).fetchall()
                    if revs:
                        avg = round(sum(r[0] for r in revs) / len(revs), 1)
                        st.write(f"**Average Rating:** {avg} ⭐ ({len(revs)} reviews)")
                        hist_df = df_from_rows(revs, ["Rating", "Review", "When"])
                        st.dataframe(hist_df, use_container_width=True, height=200)
                    else:
                        st.write("No reviews yet.")

                    with st.form(f"review_form_{item[0]}"):
                        rating = st.slider("Rating (1-5)", 1, 5, 5, key=f"rate_{item[0]}")
                        review_text = st.text_area("Write a review", key=f"text_{item[0]}")
                        submit_review = st.form_submit_button("Submit Review")
                        if submit_review:
                            cursor.execute(
                                "INSERT INTO reviews (customer_id, item_id, rating, review) VALUES (?, ?, ?, ?)",
                                (st.session_state.customer_id, item[0], rating, review_text.strip())
                            )
                            conn.commit()
                            st.success("Thank you for your review!")

            # -------- Order History + Direct Reorder --------
            st.markdown("---")
            st.subheader("📜 Your Order History")
            past_orders = cursor.execute("""
                SELECT o.id, o.date, COALESCE(SUM(oi.total_price), 0)
                FROM orders o
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE o.customer_id = ?
                GROUP BY o.id
                ORDER BY o.date DESC
            """, (st.session_state.customer_id,)).fetchall()

            if past_orders:
                hist_df = df_from_rows(past_orders, ["Order ID", "Date", "Total"])
                hist_df["Total"] = hist_df["Total"].apply(money)
                st.dataframe(hist_df, use_container_width=True)

                for order_id, date, total in past_orders:
                    if st.button(f"Reorder {order_id}", key=f"reorder_{order_id}"):
                        items = cursor.execute("""
                            SELECT item_id, quantity, total_price
                            FROM order_items
                            WHERE order_id = ?
                        """, (order_id,)).fetchall()

                        # Place new order directly (copy items and their stored subtotals)
                        cursor.execute("INSERT INTO orders (customer_id, date) VALUES (?, ?)",
                                       (st.session_state.customer_id, datetime.now()))
                        new_order_id = cursor.lastrowid
                        for item_id, qty, subtotal in items:
                            cursor.execute(
                                "INSERT INTO order_items (order_id, item_id, quantity, total_price) VALUES (?, ?, ?, ?)",
                                (new_order_id, item_id, qty, subtotal)
                            )
                        conn.commit()
                        st.success(f"✅ Order {new_order_id} placed! (Reordered from {order_id})")
            else:
                st.info("No past orders found.")

        else:
            st.info("Menu not available.")
