# 📚 BookShare — Online Used Book Donation & Resell Platform

A full-featured web app built with **Python (Flask)** + **HTML/CSS/JavaScript**, runs directly in Chrome.

---

## 🚀 Quick Start (2 steps)

```bash
# Step 1 — Install dependencies (one time only)
pip install -r requirements.txt

# Step 2 — Run the app
python app.py
```

Then open Chrome and go to: **http://localhost:5000**

---

## ✨ Features

- 🔑 Register, Login, Profile management
- 📚 Add / Edit / Delete book listings with images
- 🔍 Search & filter by title, author, category, condition, location
- 🎁 Donate books (free) or 💰 Sell them
- 📬 Send and manage donation/purchase requests
- 💬 Direct messaging between users
- ⭐ Reviews and ratings after completed exchanges
- 🌱 Social impact — donate to students, libraries, NGOs

---

## 📁 Project Structure

```
bookshare_web/
├── app.py              ← Flask backend (routes, DB, auth)
├── requirements.txt    ← pip dependencies
├── bookshare.db        ← SQLite database (auto-created)
├── templates/          ← HTML pages
│   ├── base.html
│   ├── home.html
│   ├── auth.html
│   ├── browse.html
│   ├── book_detail.html
│   ├── add_book.html
│   ├── my_books.html
│   ├── requests.html
│   ├── messages.html
│   ├── profile.html
│   └── reviews.html
└── static/
    ├── css/style.css
    ├── js/main.js
    └── uploads/        ← uploaded book cover images
```
