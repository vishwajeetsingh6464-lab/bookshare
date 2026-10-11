"""
BookShare — Flask backend + HTML frontend
Run:  python app.py
Open: http://localhost:5000
"""

import os
import sqlite3
import hashlib
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash
)

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bookshare_secret_2024")

# On Render (and most cloud hosts) the app directory is read-only;
# /tmp is always writable. Fall back to local path when running locally.
_BASE = "/tmp" if os.path.exists("/tmp") and not os.access(os.path.dirname(__file__), os.W_OK) else os.path.dirname(__file__)
DB_PATH = os.path.join(_BASE, "bookshare.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT NOT NULL UNIQUE,
            password   TEXT NOT NULL,
            location   TEXT DEFAULT '',
            bio        TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS books (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            title        TEXT NOT NULL,
            author       TEXT NOT NULL,
            category     TEXT DEFAULT '',
            condition    TEXT DEFAULT '',
            listing_type TEXT DEFAULT 'donate',
            price        REAL DEFAULT 0,
            location     TEXT DEFAULT '',
            description  TEXT DEFAULT '',
            image        TEXT DEFAULT '',
            available    INTEGER DEFAULT 1,
            created_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS requests (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id      INTEGER NOT NULL,
            requester_id INTEGER NOT NULL,
            status       TEXT DEFAULT 'pending',
            message      TEXT DEFAULT '',
            created_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(book_id)      REFERENCES books(id),
            FOREIGN KEY(requester_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id   INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            book_id     INTEGER,
            content     TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(sender_id)   REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            reviewer_id INTEGER NOT NULL,
            reviewed_id INTEGER NOT NULL,
            book_id     INTEGER,
            rating      INTEGER NOT NULL,
            comment     TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(reviewer_id) REFERENCES users(id),
            FOREIGN KEY(reviewed_id) REFERENCES users(id)
        );
    """)
    db.commit()
    db.close()


def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Auth decorator ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Helper: current user ──────────────────────────────────────────────────────
def current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    db.close()
    return dict(u) if u else None


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

# ── Home ──────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    db = get_db()
    stats = {
        "books":     db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        "donations": db.execute("SELECT COUNT(*) FROM books WHERE listing_type='donate'").fetchone()[0],
        "users":     db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "completed": db.execute("SELECT COUNT(*) FROM requests WHERE status='completed'").fetchone()[0],
    }
    recent = db.execute(
        "SELECT b.*, u.name AS owner FROM books b JOIN users u ON b.user_id=u.id "
        "WHERE b.available=1 ORDER BY b.created_at DESC LIMIT 8"
    ).fetchall()
    db.close()
    return render_template("home.html", stats=stats, recent=[dict(r) for r in recent], user=current_user())


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        pw       = request.form.get("password", "")
        pw2      = request.form.get("password2", "")
        location = request.form.get("location", "").strip()
        bio      = request.form.get("bio", "").strip()
        if not name or not email or not pw:
            flash("Name, email and password are required.", "error")
        elif pw != pw2:
            flash("Passwords do not match.", "error")
        else:
            db = get_db()
            try:
                db.execute("INSERT INTO users (name,email,password,location,bio) VALUES (?,?,?,?,?)",
                           (name, email, hash_pw(pw), location, bio))
                db.commit()
                flash("Account created! Please login.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Email already registered.", "error")
            finally:
                db.close()
    return render_template("auth.html", mode="register", user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pw    = request.form.get("password", "")
        db    = get_db()
        u     = db.execute("SELECT * FROM users WHERE email=? AND password=?",
                           (email, hash_pw(pw))).fetchone()
        db.close()
        if u:
            session["user_id"] = u["id"]
            flash(f"Welcome back, {u['name']}!", "success")
            return redirect(url_for("home"))
        flash("Invalid email or password.", "error")
    return render_template("auth.html", mode="login", user=current_user())


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("home"))


# ── Browse ────────────────────────────────────────────────────────────────────
@app.route("/browse")
def browse():
    search   = request.args.get("search", "").strip()
    category = request.args.get("category", "")
    condition= request.args.get("condition", "")
    ltype    = request.args.get("listing_type", "")
    location = request.args.get("location", "").strip()

    db    = get_db()
    query = "SELECT b.*, u.name AS owner FROM books b JOIN users u ON b.user_id=u.id WHERE b.available=1"
    params = []
    if search:
        query += " AND (b.title LIKE ? OR b.author LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if category:
        query += " AND b.category=?"
        params.append(category)
    if condition:
        query += " AND b.condition=?"
        params.append(condition)
    if ltype:
        query += " AND b.listing_type=?"
        params.append(ltype)
    if location:
        query += " AND b.location LIKE ?"
        params.append(f"%{location}%")
    query += " ORDER BY b.created_at DESC"
    books = [dict(r) for r in db.execute(query, params).fetchall()]
    db.close()

    return render_template("browse.html", books=books, user=current_user(),
                           search=search, category=category,
                           condition=condition, ltype=ltype, location=location)


@app.route("/book/<int:book_id>")
def book_detail(book_id):
    db   = get_db()
    book = db.execute("SELECT b.*, u.name AS owner, u.id AS owner_id FROM books b "
                      "JOIN users u ON b.user_id=u.id WHERE b.id=?", (book_id,)).fetchone()
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("browse"))
    book = dict(book)
    avg  = db.execute("SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE reviewed_id=?",
                      (book["owner_id"],)).fetchone()
    db.close()
    return render_template("book_detail.html", book=book, avg=dict(avg), user=current_user())


# ── Add / Edit / Delete Book ──────────────────────────────────────────────────
@app.route("/add_book", methods=["GET", "POST"])
@login_required
def add_book():
    if request.method == "POST":
        title    = request.form.get("title", "").strip()
        author   = request.form.get("author", "").strip()
        category = request.form.get("category", "")
        condition= request.form.get("condition", "")
        ltype    = request.form.get("listing_type", "donate")
        price    = float(request.form.get("price", 0) or 0)
        location = request.form.get("location", "").strip()
        desc     = request.form.get("description", "").strip()
        if not title or not author or not location:
            flash("Title, author and location are required.", "error")
        else:
            image_name = ""
            img = request.files.get("image")
            if img and img.filename:
                image_name = f"{session['user_id']}_{img.filename}"
                img.save(os.path.join(UPLOAD_FOLDER, image_name))
            db = get_db()
            db.execute("INSERT INTO books (user_id,title,author,category,condition,listing_type,price,location,description,image) "
                       "VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (session["user_id"], title, author, category, condition, ltype,
                        price if ltype == "sell" else 0, location, desc, image_name))
            db.commit()
            db.close()
            flash(f"'{title}' listed successfully!", "success")
            return redirect(url_for("my_books"))
    return render_template("add_book.html", user=current_user())


@app.route("/edit_book/<int:book_id>", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    db   = get_db()
    book = db.execute("SELECT * FROM books WHERE id=? AND user_id=?",
                      (book_id, session["user_id"])).fetchone()
    if not book:
        db.close()
        flash("Book not found.", "error")
        return redirect(url_for("my_books"))
    if request.method == "POST":
        db.execute("UPDATE books SET title=?,author=?,category=?,condition=?,listing_type=?,price=?,location=?,description=? WHERE id=?",
                   (request.form["title"], request.form["author"], request.form["category"],
                    request.form["condition"], request.form["listing_type"],
                    float(request.form.get("price", 0) or 0),
                    request.form["location"], request.form["description"], book_id))
        db.commit()
        db.close()
        flash("Book updated!", "success")
        return redirect(url_for("my_books"))
    db.close()
    return render_template("add_book.html", user=current_user(), book=dict(book))


@app.route("/delete_book/<int:book_id>", methods=["POST"])
@login_required
def delete_book(book_id):
    db = get_db()
    db.execute("DELETE FROM books WHERE id=? AND user_id=?", (book_id, session["user_id"]))
    db.commit()
    db.close()
    flash("Book deleted.", "info")
    return redirect(url_for("my_books"))


@app.route("/my_books")
@login_required
def my_books():
    db    = get_db()
    books = db.execute("SELECT * FROM books WHERE user_id=? ORDER BY created_at DESC",
                       (session["user_id"],)).fetchall()
    db.close()
    return render_template("my_books.html", books=[dict(b) for b in books], user=current_user())


# ── Requests ──────────────────────────────────────────────────────────────────
@app.route("/request_book/<int:book_id>", methods=["POST"])
@login_required
def request_book(book_id):
    uid = session["user_id"]
    msg = request.form.get("message", "").strip()
    db  = get_db()
    existing = db.execute("SELECT id FROM requests WHERE book_id=? AND requester_id=? AND status='pending'",
                          (book_id, uid)).fetchone()
    if existing:
        flash("You already have a pending request for this book.", "warning")
    else:
        db.execute("INSERT INTO requests (book_id,requester_id,message) VALUES (?,?,?)",
                   (book_id, uid, msg))
        db.commit()
        flash("Request sent!", "success")
    db.close()
    return redirect(url_for("book_detail", book_id=book_id))


@app.route("/requests")
@login_required
def requests_page():
    uid = session["user_id"]
    db  = get_db()
    incoming = db.execute(
        "SELECT r.*,b.title as book_title,u.name as requester_name,u.email as requester_email "
        "FROM requests r JOIN books b ON r.book_id=b.id JOIN users u ON r.requester_id=u.id "
        "WHERE b.user_id=? ORDER BY r.created_at DESC", (uid,)
    ).fetchall()
    outgoing = db.execute(
        "SELECT r.*,b.title as book_title,u.name as owner_name "
        "FROM requests r JOIN books b ON r.book_id=b.id JOIN users u ON b.user_id=u.id "
        "WHERE r.requester_id=? ORDER BY r.created_at DESC", (uid,)
    ).fetchall()
    db.close()
    return render_template("requests.html", user=current_user(),
                           incoming=[dict(r) for r in incoming],
                           outgoing=[dict(r) for r in outgoing])


@app.route("/update_request/<int:req_id>/<status>", methods=["POST"])
@login_required
def update_request(req_id, status):
    if status not in ("accepted", "rejected", "completed"):
        return redirect(url_for("requests_page"))
    db = get_db()
    db.execute("UPDATE requests SET status=? WHERE id=?", (status, req_id))
    if status == "accepted":
        req = db.execute("SELECT book_id FROM requests WHERE id=?", (req_id,)).fetchone()
        if req:
            db.execute("UPDATE books SET available=0 WHERE id=?", (req["book_id"],))
    db.commit()
    db.close()
    flash(f"Request marked as {status}.", "success")
    return redirect(url_for("requests_page"))


# ── Messages ──────────────────────────────────────────────────────────────────
@app.route("/messages")
@login_required
def messages():
    uid  = session["user_id"]
    db   = get_db()
    inbox = db.execute(
        "SELECT DISTINCT CASE WHEN m.sender_id=? THEN m.receiver_id ELSE m.sender_id END AS other_id, "
        "u.name AS other_name FROM messages m "
        "JOIN users u ON u.id=CASE WHEN m.sender_id=? THEN m.receiver_id ELSE m.sender_id END "
        "WHERE m.sender_id=? OR m.receiver_id=?",
        (uid, uid, uid, uid)
    ).fetchall()
    chat_with = request.args.get("with", type=int)
    partner   = None
    msgs      = []
    if chat_with:
        partner = db.execute("SELECT * FROM users WHERE id=?", (chat_with,)).fetchone()
        msgs    = db.execute(
            "SELECT m.*,u.name AS sender_name FROM messages m JOIN users u ON m.sender_id=u.id "
            "WHERE (m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?) "
            "ORDER BY m.created_at ASC",
            (uid, chat_with, chat_with, uid)
        ).fetchall()
    db.close()
    return render_template("messages.html", user=current_user(),
                           inbox=[dict(i) for i in inbox],
                           partner=dict(partner) if partner else None,
                           msgs=[dict(m) for m in msgs],
                           chat_with=chat_with)


@app.route("/send_message", methods=["POST"])
@login_required
def send_message():
    uid        = session["user_id"]
    receiver   = request.form.get("receiver_id", type=int)
    content    = request.form.get("content", "").strip()
    if receiver and content:
        db = get_db()
        db.execute("INSERT INTO messages (sender_id,receiver_id,content) VALUES (?,?,?)",
                   (uid, receiver, content))
        db.commit()
        db.close()
    return redirect(url_for("messages", **{"with": receiver}))


# ── Profile ───────────────────────────────────────────────────────────────────
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    uid = session["user_id"]
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        bio      = request.form.get("bio", "").strip()
        if name:
            db = get_db()
            db.execute("UPDATE users SET name=?,location=?,bio=? WHERE id=?",
                       (name, location, bio, uid))
            db.commit()
            db.close()
            flash("Profile updated!", "success")
        return redirect(url_for("profile"))
    db      = get_db()
    reviews = db.execute(
        "SELECT r.*,u.name AS reviewer_name FROM reviews r "
        "JOIN users u ON r.reviewer_id=u.id WHERE r.reviewed_id=? ORDER BY r.created_at DESC", (uid,)
    ).fetchall()
    avg     = db.execute("SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE reviewed_id=?", (uid,)).fetchone()
    db.close()
    return render_template("profile.html", user=current_user(),
                           reviews=[dict(r) for r in reviews], avg=dict(avg))


# ── Reviews ───────────────────────────────────────────────────────────────────
@app.route("/reviews")
@login_required
def reviews():
    uid = session["user_id"]
    db  = get_db()
    completed = db.execute(
        "SELECT r.*,b.title as book_title,b.user_id as owner_id,u.name as owner_name "
        "FROM requests r JOIN books b ON r.book_id=b.id JOIN users u ON b.user_id=u.id "
        "WHERE r.requester_id=? AND r.status='completed'", (uid,)
    ).fetchall()
    my_reviews = db.execute(
        "SELECT r.*,u.name as reviewed_name FROM reviews r "
        "JOIN users u ON r.reviewed_id=u.id WHERE r.reviewer_id=? ORDER BY r.created_at DESC", (uid,)
    ).fetchall()
    db.close()
    return render_template("reviews.html", user=current_user(),
                           completed=[dict(r) for r in completed],
                           my_reviews=[dict(r) for r in my_reviews])


@app.route("/submit_review", methods=["POST"])
@login_required
def submit_review():
    uid        = session["user_id"]
    reviewed   = request.form.get("reviewed_id", type=int)
    book_id    = request.form.get("book_id", type=int)
    rating     = request.form.get("rating", type=int)
    comment    = request.form.get("comment", "").strip()
    if reviewed and rating:
        db = get_db()
        db.execute("INSERT INTO reviews (reviewer_id,reviewed_id,book_id,rating,comment) VALUES (?,?,?,?,?)",
                   (uid, reviewed, book_id, rating, comment))
        db.commit()
        db.close()
        flash("Review submitted!", "success")
    return redirect(url_for("reviews"))


# ── Init DB on every startup (gunicorn calls module-level code) ───────────────
init_db()

# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n  BookShare is running!")
    print(f"  Open Chrome and go to:  http://localhost:{port}\n")
    app.run(host="0.0.0.0", debug=False, port=port)
