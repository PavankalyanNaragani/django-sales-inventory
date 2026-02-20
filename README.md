# 🚀 Vikmo – Sales Order & Inventory Management Lite

## 📌 Project Overview

This project is a backend implementation of a **Sales Order & Inventory Management System** built using **Django 4.2+** and **Django REST Framework**, developed as part of the Vikmo Fresher Developer Assignment.

The system simulates a simplified B2B SaaS workflow for auto parts distribution where:

- Admin manages products, dealers, and inventory
- Dealers place sales orders
- Stock validation prevents over-ordering
- Order lifecycle strictly follows business rules
- Inventory is automatically updated upon order confirmation

The primary focus of this implementation is:

- Clean relational database design
- Correct business logic enforcement
- Data integrity and transaction safety
- RESTful API design
- Clear validation and error handling

Frontend is intentionally not implemented to prioritize backend quality as per assignment guidance.

---

# ✅ Features Implemented

## 🏗 Database Models (5 Required Models)

- Product
- Inventory (One-to-One with Product)
- Dealer
- Order
- OrderItem

All relationships and constraints strictly follow assignment requirements.

---

## 📦 Core Functionalities

- Product CRUD operations
- Dealer CRUD operations
- Inventory management (Admin only)
- Draft order creation
- Multi-item order support
- Automatic price preservation at time of order
- Automatic line total and order total calculation
- Auto-generated unique order number:

```
ORD-YYYYMMDD-XXXX
```

- Strict order lifecycle enforcement:

```
Draft → Confirmed → Delivered
```

---

# 🧠 Business Logic Implementation

## ✔ 1. Stock Validation

When confirming an order:

- Each OrderItem is validated
- Requested quantity must be ≤ available stock
- If any item fails → entire order is rejected
- Error response clearly shows:
  - Product name
  - Available quantity
  - Requested quantity

---

## ✔ 2. Stock Deduction

Stock is deducted ONLY when:

```
Draft → Confirmed
```

- No stock impact in Draft state
- No stock change when Delivered
- Implemented using:
  - `transaction.atomic()`
  - `select_for_update()`

This prevents race conditions and ensures data consistency.

---

## ✔ 3. Order Status Flow Enforcement

Valid transitions:

```
Draft → Confirmed → Delivered
```

Invalid transitions rejected:

- Delivered → Draft ❌
- Confirmed → Draft ❌
- Draft → Delivered ❌

---

## ✔ 4. Order Editing Rules

- Draft orders → editable
- Confirmed/Delivered orders → locked
- Editing non-draft order returns validation error

---

## ✔ 5. Price Preservation

- `unit_price` stored inside `OrderItem`
- Future changes in Product price do NOT affect past orders

---

## ✔ 6. Data Integrity & Constraints

- Product deletion blocked if used in orders (`on_delete=PROTECT`)
- Dealer deletion blocked if orders exist
- One Inventory record per Product (OneToOneField)
- SKU is unique
- Order number is unique

---

# 🔒 Transaction & Concurrency Handling

- Order confirmation wrapped inside `transaction.atomic()`
- Inventory rows locked using `select_for_update()`
- Prevents race conditions and overselling
- Ensures database consistency under concurrent requests

---

# 🛠 Tech Stack

- Python 3.10+
- Django 4.2+
- Django REST Framework
- SQLite (default) / PostgreSQL supported
- Postman for API testing

---

# 🗂 Project Structure

## 🗂 Project Structure

```bash
django-sales-inventory/
│
├── backend_drf/
│   ├── manage.py
│   ├── requirements.txt
│   │
│   ├── sales_main/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── ...
│   │
│   ├── api/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── tests.py
│   │   └── ...
```

---

# ⚙️ Setup Instructions (Step-by-Step)

Database migrations are already included in the repository.

## 1️⃣ Clone Repository

```bash
git clone https://github.com/PavankalyanNaragani/django-sales-inventory.git
cd django-sales-inventory/backend_drf
```

---

## 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

Activate:

**Windows**
```bash
venv\Scripts\activate
```

**Mac/Linux**
```bash
source venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4️⃣ Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 5️⃣ Create Superuser

```bash
python manage.py createsuperuser
```

---

## 6️⃣ Run Development Server

```bash
python manage.py runserver
```

Access:

```
http://127.0.0.1:8000/
```

Admin:

```
http://127.0.0.1:8000/admin/
```

---

# 📡 API Documentation

### Base URL

```
/api/
```

---

## 🧾 Products

| Method | Endpoint | Description |
|--------|----------|------------|
| GET | /api/products/ | List all products with stock |
| POST | /api/products/ | Create product |
| GET | /api/products/{id}/ | Get product details |
| PUT | /api/products/{id}/ | Update product |
| DELETE | /api/products/{id}/ | Delete product |

---

## 🏢 Dealers

| Method | Endpoint | Description |
|--------|----------|------------|
| GET | /api/dealers/ | List dealers |
| POST | /api/dealers/ | Create dealer |
| GET | /api/dealers/{id}/ | Dealer details |
| PUT | /api/dealers/{id}/ | Update dealer |

---

## 📦 Orders

| Method | Endpoint | Description |
|--------|----------|------------|
| GET | /api/orders/ | List orders |
| POST | /api/orders/ | Create draft order |
| GET | /api/orders/{id}/ | Order details |
| PUT | /api/orders/{id}/ | Update draft order |
| POST | /api/orders/{id}/confirm/ | Confirm order |
| POST | /api/orders/{id}/deliver/ | Mark as delivered |

---

## 📊 Inventory (Admin Only)

| Method | Endpoint | Description |
|--------|----------|------------|
| GET | /api/inventory/ | List inventory |
| PUT | /api/inventory/{product_id}/ | Manual stock update |

---

# 📬 API Example Requests & Responses

## 🧾 Create Product

POST /api/products/

```json
{
  "name": "Brake Pad",
  "sku": "BRK001",
  "price": 500
}
```

---

## 🏢 Create Dealer

POST /api/dealers/

```json
{
  "name": "ABC Motors",
  "email": "abc@gmail.com",
  "phone": "9999999999",
  "address": "Hyderabad"
}
```

---

## 📦 Create Draft Order

POST /api/orders/

```json
{
  "dealer": 1,
  "items": [
    {
      "product": 1,
      "quantity": 10
    }
  ]
}
```

---

## ✅ Confirm Order

POST /api/orders/1/confirm/

Successful Response:

```json
{
  "message": "Order confirmed successfully."
}
```

---

## ❌ Insufficient Stock Response

```json
{
  "error": "Insufficient stock for some products.",
  "details": [
    {
      "product": "Brake Pad",
      "available": 5,
      "requested": 10
    }
  ]
}
```

---

# 📐 Database Design Summary

## Relationships

- Product ↔ Inventory (One-to-One)
- Dealer → Orders (One-to-Many)
- Order → OrderItems (One-to-Many)
- Product → OrderItems (One-to-Many)

## Key Constraints

- SKU is unique
- Order number is unique
- One inventory record per product
- Protected foreign key relationships (`on_delete=PROTECT`)

---

# 🧾 Assumptions Made

- Each product automatically creates one inventory record
- Stock deduction occurs only at order confirmation
- Inventory adjustments do not affect confirmed/delivered orders
- Draft orders can be deleted
- No custom authentication implemented beyond Django admin

---

# 👨‍💻 Author

Developed as part of Vikmo Fresher Developer Assignment.