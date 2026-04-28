from flask import Flask, render_template, redirect, session, request, url_for
import mysql.connector
from forms import RegisterForm, LoginForm, BookingForm
from db_config import DB_CONFIG_CLEAN, DB_CONFIG_BESTILLINGER

app = Flask(__name__)
app.secret_key = "hemmelig-nok"

BOOKING_OPTIONS = {
    "pakke_1": {"label": "Pakke 1: innvendig, utvendig og polering", "pris": 700},
    "pakke_2": {"label": "Pakke 2: innvendig og utvendig", "pris": 500},
    "pakke_3": {"label": "Pakke 3: enkelt behandling", "pris": 250},
    "kun_innvendig": {"label": "Kun innvendig", "pris": None},
    "kun_utvendig": {"label": "Kun utvendig", "pris": None},
    "utvendig_med_polering": {"label": "Utvendig med polering", "pris": None},
    "innvendig_utvendig": {"label": "Innvendig og utvendig", "pris": None},
    "innvendig_utvendig_polering": {"label": "Innvendig, utvendig og polering", "pris": None},
}

# DB-tilkoblinger for hver database
def get_conn_clean():
    return mysql.connector.connect(**DB_CONFIG_CLEAN)

def get_conn_bestillinger():
    return mysql.connector.connect(**DB_CONFIG_BESTILLINGER)


def ensure_bestillinger_table():
    conn = get_conn_bestillinger()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bestillinger (
            bestilling_id INT AUTO_INCREMENT PRIMARY KEY,
            navn VARCHAR(255) NOT NULL,
            epost VARCHAR(255) NOT NULL,
            biltype VARCHAR(255) NOT NULL,
            tjeneste VARCHAR(255) NOT NULL,
            pris INT NULL,
            merknad TEXT NOT NULL,
            opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


# Hovedside
@app.route("/")
def index():
    return render_template("index.html")


def redirect_to_role_home(role):
    if role == "vaskeekspert":
        return redirect("/home/vaskeekspert")
    if role == "bileier":
        return redirect("/home/bileier")
    return redirect("/login")

# Registrering
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        navn = form.name.data
        email = form.email.data
        passord = form.password.data
        rolle = form.role.data

        conn = get_conn_clean()
        cur = conn.cursor()

        cur.execute("SELECT bruker_id FROM brukere WHERE brukernavn=%s", (email,))
        existing_user = cur.fetchone()
        if existing_user:
            cur.close()
            conn.close()
            form.email.errors.append("Denne e-posten er allerede registrert")
            return render_template("register.html", form=form)

        cur.execute(
            "INSERT INTO brukere (navn, brukernavn, passord, adresse) VALUES (%s, %s, %s, %s)",
            (navn, email, passord, rolle)
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
        email = form.email.data
        passord = form.password.data

        conn = get_conn_clean()
        cur = conn.cursor()
        cur.execute(
            "SELECT navn, adresse FROM brukere WHERE brukernavn=%s AND passord=%s",
            (email, passord)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["navn"] = user[0]
            session["rolle"] = user[1]
            session["email"] = email
            return redirect_to_role_home(user[1])
        else:
            form.email.errors.append("Feil e-post eller passord")

    return render_template("login.html", form=form)


@app.route("/home/vaskeekspert")
def vaskeekspert_home():
    navn = session.get("navn")
    rolle = session.get("rolle")
    if not navn or rolle != "vaskeekspert":
        return redirect("/login")
    return render_template("expert_home.html", name=navn)


@app.route("/home/bileier")
def bileier_home():
    navn = session.get("navn")
    rolle = session.get("rolle")
    if not navn or rolle != "bileier":
        return redirect("/login")
    bestilling_lagret = request.args.get("bestilling_lagret") == "1"
    return render_template("owner_home.html", name=navn, bestilling_lagret=bestilling_lagret)


@app.route("/bestilling", methods=["GET", "POST"])
def bestilling():
    navn = session.get("navn")
    rolle = session.get("rolle")
    if not navn or rolle != "bileier":
        return redirect("/login")


    # Hent bilmodeller (merke og modell) fra DB
    car_models = []
    try:
        conn_models = get_conn_bestillinger()
        cur_models = conn_models.cursor()
        try:
            cur_models.execute("SELECT merke, modell FROM bil_modeller WHERE merke IS NOT NULL AND modell IS NOT NULL")
            rows = cur_models.fetchall()
            car_models = [f"{r[0]} {r[1]}" for r in rows]
        except Exception:
            # tabellen eller kolonnene finnes ikke eller ingen tilgjengelige rader
            car_models = []
        finally:
            cur_models.close()
            conn_models.close()
    except Exception:
        car_models = []

    form = BookingForm()
    form.tjeneste.choices = [
        (
            key,
            value["label"] if value["pris"] is None else f'{value["label"]} - {value["pris"]} kr',
        )
        for key, value in BOOKING_OPTIONS.items()
    ]

    forhåndsvalg = request.args.get("valg")
    if request.method == "GET" and forhåndsvalg in BOOKING_OPTIONS:
        form.tjeneste.data = forhåndsvalg

    if form.validate_on_submit():
        valgt_nokkel = form.tjeneste.data
        valgt_tjeneste = BOOKING_OPTIONS.get(valgt_nokkel)

        if not valgt_tjeneste:
            form.tjeneste.errors.append("Velg en gyldig behandling")
            return render_template("bestilling.html", form=form, options=BOOKING_OPTIONS)

        conn = get_conn_bestillinger()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO bestillinger (kunde_navn, pakke, bestillingstype, biltype, obs_notat)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                navn,
                valgt_tjeneste["label"],
                valgt_nokkel,
                form.biltype.data,
                form.merknad.data,
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("bileier_home", bestilling_lagret="1"))

    return render_template(
        "bestilling.html", form=form, options=BOOKING_OPTIONS, car_models=car_models
    )


@app.route("/welcome")
def welcome_redirect():
    rolle = session.get("rolle")
    if not rolle:
        return redirect("/login")
    return redirect_to_role_home(rolle)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run()