from flask import Flask, render_template, redirect, session
import mysql.connector
from forms import RegisterForm, LoginForm

app = Flask(__name__)
app.secret_key = "hemmelig-nok"

# Enkel DB-tilkobling
def get_conn():
    return mysql.connector.connect(
        host="localhost",
        user="",
        password="",
        database=""
    )

# Hovedside
@app.route("/")
def index():
    return render_template("index.html")

# Registrering
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        navn = form.name.data
        brukernavn = form.username.data
        passord = form.password.data
        adresse = form.address.data

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO brukere (navn, brukernavn, passord, adresse) VALUES (%s, %s, %s, %s)",
            (navn, brukernavn, passord, adresse)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/login")

    return render_template("register.html", form=form)

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        brukernavn = form.username.data
        passord = form.password.data

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT navn FROM brukere WHERE brukernavn=%s AND passord=%s",
            (brukernavn, passord)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session['navn'] = user[0]  # lagrer navnet i session
            return redirect("/welcome")
        else:
            form.username.errors.append("Feil brukernavn eller passord")

    return render_template("login.html", form=form)

# Velkomstside
@app.route("/welcome")
def welcome():
    navn = session.get('navn')  # Hent navn fra session
    if not navn:
        return redirect("/login")  # send tilbake til login om ikke logget inn
    return render_template("welcome.html", name=navn)

if __name__ == "__main__":
    app.run()