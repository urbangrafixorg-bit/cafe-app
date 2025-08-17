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
""")
conn.commit()

# ----------------------------
# App Config
# ----------------------------
st.set_page_config(page_title="Cafe Central", page_icon="☕", layout="wide")
st.title("☕ Cafe Central Management System")

role = st.sidebar.radio("Login as:", ["Dashboard", "Customer", "Admin"])

# ----------------------------
# Dashboard
# ----------------------------
if role == "Dashboard":
    st.header("📊 Overview Dashboard")
    st.write("Welcome to **Cafe Central**! Here's a quick look at our cafe activity.")

    total_customers = cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_orders = cursor.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_sales = cursor.execute("SELECT COALESCE(SUM(total_price), 0) FROM order_items").fetchone()[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Customers", total_customers)
    with col2:
        st.metric("🛍️ Orders", total_orders)
    with col3:
        st.metric("💰 Sales", f"${total_sales:,.2f}")

    st.markdown("---")

    st.subheader("🆕 Recent Orders")
    recent_orders = cursor.execute("""
        SELECT o.id, c.name, o.date, SUM(oi.total_price) as amount
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        LEFT JOIN order_items oi ON oi.order_id = o.id
        GROUP BY o.id
        ORDER BY o.date DESC LIMIT 5
    """).fetchall()

    if recent_orders:
        st.table(recent_orders)
    else:
        st.info("No orders yet.")

# ----------------------------
# Admin Section
# ----------------------------
elif role == "Admin":
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
        st.table(customers) if customers else st.info("No customers found.")

    elif choice == "View Orders":
        st.subheader("🛒 Orders List")
        orders = cursor.execute("SELECT * FROM orders").fetchall()
        st.table(orders) if orders else st.info("No orders placed yet.")

    elif choice == "Manage Menu":
        st.subheader("📋 Manage Menu")
        menu_items = cursor.execute("SELECT * FROM menu").fetchall()
        st.table(menu_items) if menu_items else st.info("Menu is empty.")

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
        st.subheader("📊 Sales Report")

        report_type = st.radio("Select Report Type:", ["Daily", "Monthly"], horizontal=True)

        if report_type == "Daily":
            report = cursor.execute("""
                SELECT strftime('%Y-%m-%d', o.date) AS day, SUM(oi.total_price) AS total_sales
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                GROUP BY strftime('%Y-%m-%d', o.date)
                ORDER BY day DESC
            """).fetchall()

            if report:
                st.write("### 🗓 Daily Sales")
                st.table(report)
                st.line_chart({r[0]: r[1] for r in report})
            else:
                st.info("No daily sales data available yet.")

        else:  # Monthly
            report = cursor.execute("""
                SELECT strftime('%Y-%m', o.date) AS month, SUM(oi.total_price) AS total_sales
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                GROUP BY strftime('%Y-%m', o.date)
                ORDER BY month DESC
            """).fetchall()

            if report:
                st.write("### 📅 Monthly Sales")
                st.table(report)
                st.bar_chart({r[0]: r[1] for r in report})
            else:
                st.info("No monthly sales data available yet.")

# ----------------------------
# Customer Section
# ----------------------------
elif role == "Customer":
    st.header("🙋 Customer Portal")

    st.subheader("New Customer Registration")
    with st.form("register_form"):
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
        register_btn = st.form_submit_button("Register")
        if register_btn and name and phone and email:
            cursor.execute("INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)", 
                           (name, phone, email))
            conn.commit()
            customer_id = cursor.lastrowid
            st.success(f"Registered successfully! Your Customer ID is {customer_id}")

    st.markdown("---")

    st.subheader("Existing Customer Login")
    customer_id = st.number_input("Enter Customer ID", min_value=1, step=1)
    if st.button("Login"):
        customer = cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if customer:
            st.success(f"Welcome back, {customer[1]}!")

            menu_tab, order_tab = st.tabs(["🍽️ View Menu", "🛍️ Place Order"])

            with menu_tab:
                menu_items = cursor.execute("SELECT * FROM menu").fetchall()
                st.table(menu_items) if menu_items else st.info("Menu not available.")

            with order_tab:
                menu_items = cursor.execute("SELECT * FROM menu").fetchall()
                if menu_items:
                    order = []
                    st.write("Select items to order:")
                    for item in menu_items:
                        qty = st.number_input(
                            f"{item[1]} (${item[3]})", min_value=0, step=1, key=f"item_{item[0]}"
                        )
                        if qty > 0:
                            order.append((item[0], qty, float(item[3]) * qty))

                    upi_number = st.text_input("Enter UPI Number for payment")

                    if st.button("Place Order"):
                        if order:
                            cursor.execute(
                                "INSERT INTO orders (customer_id, date, upi_number) VALUES (?, ?, ?)", 
                                (customer_id, datetime.now(), upi_number)
                            )
                            order_id = cursor.lastrowid
                            for item_id, qty, total_price in order:
                                cursor.execute(
                                    "INSERT INTO order_items (order_id, item_id, quantity, total_price) VALUES (?, ?, ?, ?)",
                                    (order_id, item_id, qty, total_price)
                                )
                            conn.commit()
                            st.success(f"Order placed successfully! Your Order ID is {order_id}")
                        else:
                            st.warning("No items selected for order.")
                else:
                    st.info("Menu not available.")
        else:
            st.error("Invalid Customer ID.")
