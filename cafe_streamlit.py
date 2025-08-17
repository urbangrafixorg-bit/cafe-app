
# streamlit_app.py
import streamlit as st
import mysql.connector
from datetime import datetime

# ----------------------------
# Database Connection Function
# ----------------------------
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        database="cafe_central",
        user="root",
        passwd="root"
    )

# ----------------------------
# App Title
# ----------------------------
st.set_page_config(page_title="Cafe Central", page_icon="☕", layout="wide")
st.title("☕ Cafe Central Management System")

# ----------------------------
# Role Selection
# ----------------------------
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

    conn = get_connection()

    if choice == "View Customers":
        st.subheader("👥 Customers List")
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers")
        customers = cursor.fetchall()
        cursor.close()
        if customers:
            st.table(customers)
        else:
            st.info("No customers found.")

    elif choice == "View Orders":
        st.subheader("🛒 Orders List")
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders")
        orders = cursor.fetchall()
        cursor.close()
        if orders:
            st.table(orders)
        else:
            st.info("No orders placed yet.")

    elif choice == "Manage Menu":
        st.subheader("📋 Manage Menu")

        # Display current menu
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM menu")
        menu_items = cursor.fetchall()
        cursor.close()
        if menu_items:
            st.table(menu_items)
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
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO menu (name, category, price) VALUES (%s, %s, %s)", 
                                   (name, category, price))
                    conn.commit()
                    cursor.close()
                    st.success(f"Added '{name}' to the menu!")

        elif action == "Remove Item":
            item_id = st.number_input("Enter Item ID to remove", min_value=1, step=1)
            if st.button("Remove Item"):
                cursor = conn.cursor()
                cursor.execute("DELETE FROM menu WHERE id = %s", (item_id,))
                conn.commit()
                cursor.close()
                st.warning(f"Item with ID {item_id} removed.")

        elif action == "Update Item":
            item_id = st.number_input("Enter Item ID to update", min_value=1, step=1)
            if st.button("Load Item"):
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM menu WHERE id = %s", (item_id,))
                item = cursor.fetchone()
                cursor.close()
                if item:
                    with st.form("update_item_form"):
                        new_name = st.text_input("Item Name", item["name"])
                        new_category = st.text_input("Category", item["category"])
                        new_price = st.number_input("Price", value=float(item["price"]))
                        submitted = st.form_submit_button("Update Item")
                        if submitted:
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE menu SET name=%s, category=%s, price=%s WHERE id=%s",
                                (new_name, new_category, new_price, item_id)
                            )
                            conn.commit()
                            cursor.close()
                            st.success("Item updated successfully.")
                else:
                    st.error("Item not found.")

    elif choice == "View Sales Report":
        st.subheader("📊 Monthly Sales Report")
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                MONTH(o.date) AS month, 
                SUM(oi.total_price) AS total_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            GROUP BY MONTH(o.date)
        """)
        report = cursor.fetchall()
        cursor.close()

        if report:
            st.table(report)
            st.bar_chart({f"Month {r['month']}": r['total_sales'] for r in report})
        else:
            st.info("No sales data available yet.")

    conn.close()

# ----------------------------
# Customer Section
# ----------------------------
else:
    st.header("🙋 Customer Portal")
    conn = get_connection()

    # Registration
    st.subheader("New Customer Registration")
    with st.form("register_form"):
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
        register_btn = st.form_submit_button("Register")
        if register_btn and name and phone and email:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO customers (name, phone, email) VALUES (%s, %s, %s)", 
                           (name, phone, email))
            conn.commit()
            customer_id = cursor.lastrowid
            cursor.close()
            st.success(f"Registered successfully! Your Customer ID is {customer_id}")

    st.markdown("---")

    # Existing customer
    st.subheader("Existing Customer Login")
    customer_id = st.number_input("Enter Customer ID", min_value=1, step=1)
    if st.button("Login"):
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
        customer = cursor.fetchone()
        cursor.close()

        if customer:
            st.success(f"Welcome back, {customer['name']}!")

            menu_tab, order_tab = st.tabs(["🍽️ View Menu", "🛍️ Place Order"])

            # View Menu
            with menu_tab:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM menu")
                menu_items = cursor.fetchall()
                cursor.close()
                if menu_items:
                    st.table(menu_items)
                else:
                    st.info("Menu not available.")

            # Place Order
            with order_tab:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM menu")
                menu_items = cursor.fetchall()
                cursor.close()

                if menu_items:
                    order = []
                    st.write("Select items to order:")

                    for item in menu_items:
                        qty = st.number_input(
                            f"{item['name']} (${item['price']})", min_value=0, step=1, key=f"item_{item['id']}"
                        )
                        if qty > 0:
                            order.append((item["id"], qty, float(item["price"]) * qty))

                    upi_number = st.text_input("Enter UPI Number for payment")

                    if st.button("Place Order"):
                        if order:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO orders (customer_id, date, upi_number) VALUES (%s, %s, %s)", 
                                           (customer_id, datetime.now(), upi_number))
                            order_id = cursor.lastrowid
                            for item_id, qty, total_price in order:
                                cursor.execute(
                                    "INSERT INTO order_items (order_id, item_id, quantity, total_price) VALUES (%s, %s, %s, %s)",
                                    (order_id, item_id, qty, total_price)
                                )
                            conn.commit()
                            cursor.close()
                            st.success(f"Order placed successfully! Your Order ID is {order_id}")
                        else:
                            st.warning("No items selected for order.")

        else:
            st.error("Invalid Customer ID.")

    conn.close()
