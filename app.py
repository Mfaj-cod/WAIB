import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

    db_path = os.getenv("SQLITE_PATH", "waib.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db = SQLAlchemy(app)

    # -------------------------------
    # Models
    # -------------------------------
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password_hash = db.Column(db.String(255), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        def set_password(self, password: str):
            self.password_hash = generate_password_hash(password)

        def check_password(self, password: str) -> bool:
            return check_password_hash(self.password_hash, password)

    class Template(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(120), nullable=False)
        price = db.Column(db.Integer, nullable=False)  # in USD for internal
        category = db.Column(db.String(80), nullable=False)
        img = db.Column(db.String(255), nullable=False)
        features_json = db.Column(db.Text, nullable=False, default="[]")

        @property
        def features(self):
            try:
                return json.loads(self.features_json or "[]")
            except Exception:
                return []

        @features.setter
        def features(self, value):
            self.features_json = json.dumps(value or [])

    class ContactMessage(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(120), nullable=False)
        email = db.Column(db.String(120), nullable=False)
        message = db.Column(db.Text, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # -------------------------------
    # App helpers
    # -------------------------------
    def current_user():
        username = session.get("user")
        if not username:
            return None
        return User.query.filter_by(username=username).first()

    # -------------------------------
    # DB init & seed
    # -------------------------------
    with app.app_context():
        db.create_all()

        if db.session.query(func.count(Template.id)).scalar() == 0:
            seed = [
                {
                    "title": "SaaS Spark",
                    "price": 99,
                    "category": "Business",
                    "img": "https://colorlib.com/wp/wp-content/uploads/sites/2/endgam-free-template.jpg",
                    "features": ["Hero + Pricing", "Blog", "Bootstrap 5", "SEO-ready"],
                },
                {
                    "title": "Cafe Cozy",
                    "price": 49,
                    "category": "Hospitality",
                    "img": "https://colorlib.com/wp/wp-content/uploads/sites/2/hostza-free-template.jpg",
                    "features": ["Menu grid", "Booking form", "Sticky navbar"],
                },
                {
                    "title": "Portfolio Pro",
                    "price": 79,
                    "category": "Portfolio",
                    "img": "https://uicookies.com/wp-content/uploads/2018/06/interior-free-web-design-templates.jpg",
                    "features": ["Masonry gallery", "Case studies", "Contact form"],
                },
                {
                    "title": "Edu Learn",
                    "price": 129,
                    "category": "Education",
                    "img": "https://colorlib.com/wp/wp-content/uploads/sites/2/videograph-free-template.jpg",
                    "features": ["Course cards", "FAQ", "Newsletter"],
                },
                {
                    "title": "Event Vibe",
                    "price": 59,
                    "category": "Events",
                    "img": "https://uicookies.com/wp-content/uploads/2018/06/dorne-free-magazine-website-templates.jpg",
                    "features": ["Agenda", "Speakers", "Ticket CTA"],
                },
                {
                    "title": "Startup Hub",
                    "price": 109,
                    "category": "Business",
                    "img": "https://uicookies.com/wp-content/uploads/2018/08/tough-free-industrial-website-templates.jpg",
                    "features": ["Hero section", "Testimonials", "Contact form"],
                }
            ]
            for s in seed:
                t = Template(
                    title=s["title"],
                    price=s["price"],
                    category=s["category"],
                    img=s["img"],
                )
                t.features = s["features"]
                db.session.add(t)
            db.session.commit()


    # -------------------------------
    # Routes
    # -------------------------------
    @app.get("/")
    def home():
        showcase = Template.query.order_by(Template.id.asc()).limit(3).all()
        return render_template("index.html", user=current_user(), showcase=showcase)

    @app.get("/about")
    def about():
        return render_template("about.html", user=current_user())

    @app.get("/faq")
    def faq():
        return render_template("faq.html", user=current_user())

    @app.get("/templates")
    def templates_page():
        price = request.args.get("price")  # 'all' | '0-60' | '60-100' | '100+'
        q = Template.query
        if price == "0-60":
            q = q.filter(Template.price <= 60)
        elif price == "60-100":
            q = q.filter((Template.price > 60) & (Template.price <= 100))
        elif price == "100+":
            q = q.filter(Template.price > 100)
        items = q.order_by(Template.price.asc()).all()
        return render_template("templates.html", user=current_user(), items=items, active_price=price or "all")



    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            if "user" in session:
                user = User.query.filter_by(username=session["user"]).first()
                name = user.username
                email = user.email
            else:
                name = request.form.get("name", "").strip()
                email = request.form.get("email", "").strip()
            
            message = request.form.get("message", "").strip()

            if not message:
                flash("Please write something to send a message.", "danger")
                return redirect(url_for("contact"))

            if not name or not email:
                flash("Please fill in all fields.", "danger")
                return redirect(url_for("contact"))
            else:
                cm = ContactMessage(name=name, email=email, message=message)
                try:
                    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
                        connection.starttls()
                        connection.login(os.getenv("COMPANY_EMAIL"), os.getenv("EMAIL_PASSWORD"))
                        connection.sendmail(
                            from_addr=os.getenv("COMPANY_EMAIL"),
                            to_addrs=os.getenv("COMPANY_EMAIL"),
                            msg=f"Subject: New Contact Message\n\nFrom: {name} <{email}>\n\n{message}"
                        )
                except Exception as e:
                    flash(f"Failed to send info email: {e}", "danger")

                db.session.add(cm)
                db.session.commit()
                flash("Thanks! Your message has been received. We'll get back to you soon.", "success")
                return redirect(url_for("contact"))
        return render_template("contact.html", user=current_user())




    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session["user"] = user.username
                flash("Welcome back!", "success")
                return redirect(url_for("home"))
            flash("Invalid username or password.", "danger")
        return render_template("login.html", user=current_user())





    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            confirm = request.form.get("confirm", "").strip()

            if not username or not email or not password:
                flash("Please complete all fields.", "danger")
            elif password != confirm:
                flash("Passwords do not match.", "danger")
            elif User.query.filter((User.username == username) | (User.email == email)).first():
                flash("Username or email already exists.", "warning")
            

            domain = email.split('@')[-1]
            if domain not in ['gmail.com', 'hotmail.com', 'yahoo.com', 'outlook.com']:
                flash("Please use a valid email address.", "danger")
                return redirect(url_for("register"))

            elif len(password) < 6:
                flash("Password must be at least 6 characters long.", "danger")
                return redirect(url_for("register"))
            elif not any(char.isdigit() for char in password):
                flash("Password must contain at least one number.", "danger")
                return redirect(url_for("register"))
            elif not any(char.isalpha() for char in password):
                flash("Password must contain at least one letter.", "danger")
                return redirect(url_for("register"))
            elif not any(char in "!@#$%^&*()-+" for char in password):
                flash("Password must contain at least one special character.", "danger")
                return redirect(url_for("register"))
            else:
                u = User(username=username, email=email)
                u.set_password(password)
                try:
                    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
                        connection.starttls()
                        connection.login(os.getenv("COMPANY_EMAIL"), os.getenv("EMAIL_PASSWORD"))
                        connection.sendmail(
                            from_addr=os.getenv("COMPANY_EMAIL"),
                            to_addrs=email,
                            msg=f"📩 Welcome\nSubject: 🎉 Welcome to WAIB -- Let's Build Something Amazing!\n\nHi {username},\n\nWelcome to WAIB! 🚀\nWe're excited to have you on board. At WAIB, we specialize in building modern, responsive, and customer-winning websites tailored to your needs.\n\nHere's what you can do next:\n\n🔑 Log in to your account and explore our dashboard\n\n🎨 Browse our ready-to-use website templates\n\n📞 Reach out to us anytime for support or customization\n\nWe can't wait to help you bring your ideas online.\n\nCheers,\nThe WAIB Team\nwaib.com"
                        )
                except Exception as e:
                    pass
                db.session.add(u)
                db.session.commit()
                flash("Registration successful. You can now log in.", "success")
                return redirect(url_for("login"))
        return render_template("register.html", user=current_user())





    @app.get("/logout")
    def logout():
        session.pop("user", None)
        flash("Logged out.", "info")
        return redirect(url_for("home"))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html", user=current_user()), 404

    return app



app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
