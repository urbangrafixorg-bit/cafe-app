# streamlit_app.py
import streamlit as st
import sqlite3
from datetime import datetime

# ----------------------------
# Database Setup
# ----------------------------
conn = sqlite3.connect("cafe_central.db", check_same_thread=False)
cursor = conn.cursor()

# Create tables if they don’t exist
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

# ----------------------------
# App UI
# ----------------------------
st.set_page_config(page_title="Cafe Central", page_icon="☕", layout="wide")
st.title("☕ Cafe Central Management System")

role = st.sidebar.radio("Login as:", ["Customer", "Admin"])

# ----------------------------
# Admin Section
# ----------------------------
if role == "Admin":
    st.header("🔑 Admin Dashboard")
    choice = st.sidebar.selectbox("Choose an action", [
        "View Customers",
        "View Orders",
        "Manage Menu",
        "View Sales Report"
    ])

    if choice == "View Customers":
        st.subheader("👥 Customers List")
        customers = cursor.execute("SELECT * FROM customers").fetchall()
        if customers:
            st.table(customers)
        else:
            st.info("No customers found.")

    elif choice == "View Orders":
        st.subheader("🛒 Orders List")
        orders = cursor.execute("SELECT * FROM orders").fetchall()
        if orders:
            st.table(orders)
        else:
            st.info("No orders placed yet.")

    elif choice == "Manage Menu":
        st.subheader("📋 Manage Menu")
        menu_items = cursor.execute("SELECT * FROM menu").fetchall()
        if menu_items:
            for item in menu_items:
                reviews = cursor.execute("""
                    SELECT rating FROM reviews WHERE item_id = ?
                """, (item[0],)).fetchall()
                avg_rating = sum(r[0] for r in reviews) / len(reviews) if reviews else 0
                st.write(f"ID: {item[0]} | {item[1]} | Category: {item[2]} | Price: ${item[3]:.2f} | Avg Rating: {avg_rating:.1f} ⭐")
        else:
            st.info("Menu is empty.")

        st.markdown("---")
        action = st.radio("Choose Action:", ["Add Item", "Remove Item", "Update Item"])

        if action == "Add Item":
            with st.form("add_item_form"):
                name = st.text_input("Item Name")
                category = st.text_input("Category")
                price = st.number_input("Price", min_value=0.0, format="%.2f")
                submitted = st.form_submit_button("Add Item")
                if submitted and name and category:
                    cursor.execute("INSERT INTO menu (name, category, price) VALUES (?, ?, ?)", 
                                   (name, category, price))
                    conn.commit()
                    st.success(f"Added '{name}' to the menu!")

        elif action == "Remove Item":
            item_id = st.number_input("Enter Item ID to remove", min_value=1, step=1)
            if st.button("Remove Item"):
                cursor.execute("DELETE FROM menu WHERE id = ?", (item_id,))
                conn.commit()
                st.warning(f"Item with ID {item_id} removed.")

        elif action == "Update Item":
            item_id = st.number_input("Enter Item ID to update", min_value=1, step=1)
            if st.button("Load Item"):
                item = cursor.execute("SELECT * FROM menu WHERE id = ?", (item_id,)).fetchone()
                if item:
                    with st.form("update_item_form"):
                        new_name = st.text_input("Item Name", item[1])
                        new_category = st.text_input("Category", item[2])
                        new_price = st.number_input("Price", value=float(item[3]))
                        submitted = st.form_submit_button("Update Item")
                        if submitted:
                            cursor.execute(
                                "UPDATE menu SET name=?, category=?, price=? WHERE id=?",
                                (new_name, new_category, new_price, item_id)
                            )
                            conn.commit()
                            st.success("Item updated successfully.")
                else:
                    st.error("Item not found.")

    elif choice == "View Sales Report":
        st.subheader("📊 Monthly Sales Report")
        monthly_report = cursor.execute("""
            SELECT strftime('%m', o.date) AS month, SUM(oi.total_price) AS total_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            GROUP BY strftime('%m', o.date)
        """).fetchall()
        if monthly_report:
            st.table(monthly_report)
            st.bar_chart({f"Month {r[0]}": r[1] for r in monthly_report})
        else:
            st.info("No sales data available yet.")

        st.subheader("📅 Daily Sales Report")
        daily_report = cursor.execute("""
            SELECT strftime('%Y-%m-%d', o.date) AS day, SUM(oi.total_price) AS total_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            GROUP BY strftime('%Y-%m-%d', o.date)
        """).fetchall()
        if daily_report:
            st.table(daily_report)
            st.bar_chart({r[0]: r[1] for r in daily_report})
        else:
            st.info("No daily sales data yet.")

# ----------------------------
# Customer Section
# ----------------------------
elif role == "Customer":
    st.header("🙋 Customer Portal")

    # New Customer Registration
    st.subheader("New Customer Registration")
    with st.form("register_form"):
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
        register_btn = st.form_submit_button("Register")
        if register_btn and name and phone and email:
            cursor.execute(
                "INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)", 
                (name, phone, email)
            )
            conn.commit()
            customer_id = cursor.lastrowid
            st.success(f"Registered successfully! Your Customer ID is {customer_id}")

    st.markdown("---")

    # Existing Customer Login
    if "customer_id" not in st.session_state:
        st.session_state.customer_id = None

    if st.session_state.customer_id is None:
        customer_id_input = st.number_input("Enter Customer ID", min_value=1, step=1)
        if st.button("Login"):
            customer = cursor.execute(
                "SELECT * FROM customers WHERE id = ?", (customer_id_input,)
            ).fetchone()
            if customer:
                st.session_state.customer_id = customer[0]
                st.success(f"Welcome back, {customer[1]}!")
            else:
                st.error("Invalid Customer ID.")

    if st.session_state.customer_id:
        customer = cursor.execute(
            "SELECT * FROM customers WHERE id = ?", (st.session_state.customer_id,)
        ).fetchone()
        st.success(f"Welcome back, {customer[1]}!")

        # Initialize order if not in session state
        if "order" not in st.session_state:
            st.session_state.order = []

        menu_items = cursor.execute("SELECT * FROM menu").fetchall()
        if menu_items:
            st.subheader("🍽️ Menu")
            with st.form("menu_form"):
                order_quantities = {}
                for item in menu_items:
                    order_quantities[item[0]] = st.number_input(
                        f"{item[1]} (${item[3]})",
                        min_value=0,
                        step=1,
                        key=f"item_{item[0]}"
                    )
                submit_order = st.form_submit_button("Update Cart")

            # Update session state order list
            st.session_state.order = []
            total_amount = 0
            summary_data = []
            for item_id, qty in order_quantities.items():
                if qty > 0:
                    price, name = cursor.execute(
                        "SELECT price, name FROM menu WHERE id = ?", (item_id,)
                    ).fetchone()
                    subtotal = price * qty
                    st.session_state.order.append((item_id, qty, subtotal))
                    summary_data.append([name, qty, f"${subtotal:.2f}"])
                    total_amount += subtotal

            if st.session_state.order:
                st.markdown("---")
                st.subheader("📝 Order Summary")
                st.table(summary_data)
                st.write(f"**Total: ${total_amount:.2f}**")

                if st.button("Place Order"):
                    cursor.execute(
                        "INSERT INTO orders (customer_id, date) VALUES (?, ?)", 
                        (st.session_state.customer_id, datetime.now())
                    )
                    order_id = cursor.lastrowid
                    for item_id, qty, subtotal in st.session_state.order:
                        cursor.execute(
                            "INSERT INTO order_items (order_id, item_id, quantity, total_price) VALUES (?, ?, ?, ?)",
                            (order_id, item_id, qty, subtotal)
                        )
                    conn.commit()
                    st.success(f"✅ Order placed successfully! Your Order ID is {order_id}")
                    st.session_state.order = []  # Clear cart

            # ----------------------------
            # Ratings & Reviews
            st.markdown("---")
            st.subheader("⭐ Rate & Review Menu Items")
            for item in menu_items:
                with st.expander(f"{item[1]} (${item[3]})"):
                    st.write(f"Category: {item[2]}")
                    reviews = cursor.execute("""
                        SELECT rating, review FROM reviews WHERE item_id = ?
                    """, (item[0],)).fetchall()
                    if reviews:
                        avg_rating = sum(r[0] for r in reviews) / len(reviews)
                        st.write(f"**Average Rating:** {avg_rating:.1f} ⭐")
                        for r in reviews:
                            st.write(f"Rating: {r[0]} ⭐ | Review: {r[1]}")
                    else:
                        st.write("No reviews yet.")

                    with st.form(f"review_form_{item[0]}"):
                        rating = st.slider("Rating (1-5)", 1, 5, 5)
                        review_text = st.text_area("Write a review")
                        submit_review = st.form_submit_button("Submit Review")
                        if submit_review:
                            cursor.execute("""
                                INSERT INTO reviews (customer_id, item_id, rating, review)
                                VALUES (?, ?, ?, ?)
                            """, (st.session_state.customer_id, item[0], rating, review_text))
                            conn.commit()
                            st.success("Thank you for your review!")

            # ----------------------------
            # Order History & Reorder
            st.markdown("---")
            st.subheader("📜 Your Order History")
            past_orders = cursor.execute("""
                SELECT o.id, o.date, SUM(oi.total_price) 
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE o.customer_id = ?
                GROUP BY o.id
                ORDER BY o.date DESC
            """, (st.session_state.customer_id,)).fetchall()

            if past_orders:
                for order_id, date, total in past_orders:
                    st.write(f"**Order ID:** {order_id} | **Date:** {date} | **Total:** ${total:.2f}")
                    if st.button(f"Reorder {order_id}", key=f"reorder_{order_id}"):
                        st.session_state.order = []
                        items = cursor.execute("""
                            SELECT item_id, quantity, total_price
                            FROM order_items
                            WHERE order_id = ?
                        """, (order_id,)).fetchall()
                        for item_id, qty, subtotal in items:
                            st.session_state.order.append((item_id, qty, subtotal))
                        st.success(f"Loaded Order {order_id} into your cart!")
            else:
                st.info("No past orders found.")
        else:
            st.info("Menu not available.")
