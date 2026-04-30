from flask import Flask, render_template, redirect, session, request, url_for
import mysql.connector
from datetime import time
from forms import RegisterForm, LoginForm, BookingForm
from db_config import DB_CONFIG_CLEAN, DB_CONFIG_BESTILLINGER
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "hemmelig-nok"

# Egen tilkobling per database, siden appen leser og skriver til to ulike skjemaer.
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
            bestillingsdato DATE NULL,
            bestillingstid TIME NULL,
            pris INT NULL,
            merknad TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            vaskeekspert_email VARCHAR(255) NULL,
            opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


def ensure_bestillinger_columns():
    """Ensure status and vaskeekspert_email columns exist for expert acceptance workflow."""
    conn = get_conn_bestillinger()
    cur = conn.cursor()
    try:
        cur.execute(
            "ALTER TABLE bestillinger ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending'"
        )
        cur.execute(
            "ALTER TABLE bestillinger ADD COLUMN IF NOT EXISTS vaskeekspert_email VARCHAR(255) NULL"
        )
        # Backfill existing rows so old bookings become visible as pending.
        cur.execute(
            "UPDATE bestillinger SET status = 'pending' WHERE status IS NULL OR status = ''"
        )
        conn.commit()
    except Exception as e:
        print(f"Note: Could not add columns (may already exist): {e}")
    finally:
        cur.close()
        conn.close()


# Hovedside
@app.route("/")
def index():
    # Forsiden er bare en enkel inngangsside.
    return render_template("index.html")


def redirect_to_role_home(role):
    # Send brukeren til riktig startside basert på rollen som ble lagret i session.
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
        # Registrering bruker e-post som innloggingsnavn.
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

        hashed_password = generate_password_hash(passord, method='pbkdf2:sha256')
        cur.execute(
            "INSERT INTO brukere (navn, brukernavn, passord, adresse) VALUES (%s, %s, %s, %s)",
            (navn, email, hashed_password, rolle)
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
        # Hent brukerdata og verifiser passord før session settes.
        email = form.email.data
        passord = form.password.data

        conn = get_conn_clean()
        cur = conn.cursor()
        cur.execute(
            "SELECT navn, adresse, passord FROM brukere WHERE brukernavn=%s",
            (email,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user[2], passord):
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
    # Eksperthjemmesiden trenger bare navnet for å vise en personlig velkomst.
    return render_template("vasker_h.html", name=navn)


@app.route("/home/bileier")
def bileier_home():
    navn = session.get("navn")
    rolle = session.get("rolle")
    if not navn or rolle != "bileier":
        return redirect("/login")
    # Query-parameteren brukes for å vise en bekreftelse etter vellykket bestilling.
    bestilling_lagret = request.args.get("bestilling_lagret") == "1"
    return render_template("bileier_h.html", name=navn, bestilling_lagret=bestilling_lagret)


# Bileier: Se egne bestillinger
@app.route("/mine-bestillinger")
def mine_bestillinger():
    navn = session.get("navn")
    rolle = session.get("rolle")
    if not navn or rolle != "bileier":
        return redirect("/login")

    try:
        conn = get_conn_bestillinger()
        cur = conn.cursor()
        # Hent bestillinger for innlogget bileier. Skjemaet har historisk hatt ulike kolonnenavn.
        cur.execute(
            """
            SELECT bestilling_id, biltype, pakke, pris, status, obs_notat
            FROM bestillinger
            WHERE kunde_navn = %s
            ORDER BY opprettet DESC
            """,
            (navn,)
        )
        bestillinger = []
        for row in cur.fetchall():
            status_text = "Venter på svar"
            if row[4] == "accepted":
                status_text = "Godtatt"
            elif row[4] == "rejected":
                status_text = "Avslått"
            bestillinger.append({
                'id': row[0],
                'biltype': row[1],
                'tjeneste': row[2],
                'pris': row[3],
                'status': status_text,
                'merknad': row[5]
            })
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error loading mine bestillinger: {e}")
        bestillinger = []

    return render_template("mine_bestillinger.html", bestillinger=bestillinger, name=navn)


@app.route("/bestilling", methods=["GET", "POST"])
def bestilling():
    navn = session.get("navn")
    rolle = session.get("rolle")
    if not navn or rolle != "bileier":
        return redirect("/login")


    # Hent bilmodeller og bygg en visningsliste som brukes av autofullføring i skjemaet.
    car_models = []
    model_type_map = {}
    try:
        conn_models = get_conn_bestillinger()
        cur_models = conn_models.cursor()
        try:
            cur_models.execute(
                """
                SELECT merke, modell, type
                FROM bil_modeller
                WHERE merke IS NOT NULL AND modell IS NOT NULL
                """
            )
            rows = cur_models.fetchall()
            for merke, modell, bilklasse in rows:
                display_name = f"{merke} {modell}"
                car_models.append(display_name)
                if bilklasse:
                    model_type_map[display_name] = bilklasse.strip().lower()
        except Exception:
            # tabellen eller kolonnene finnes ikke eller ingen tilgjengelige rader
            car_models = []
            model_type_map = {}
        finally:
            cur_models.close()
            conn_models.close()
    except Exception:
        car_models = []
        model_type_map = {}

    # Hent tilgjengelige behandlinger og prisene deres fra databasen.
    behandlinger = {}
    behandling_choices = []
    try:
        conn_behandlinger = get_conn_bestillinger()
        cur_behandlinger = conn_behandlinger.cursor()
        cur_behandlinger.execute(
            """
            SELECT kode, navn, pris
            FROM behandlinger
            ORDER BY behandling_id
            """
        )
        rows = cur_behandlinger.fetchall()
        for kode, navn_behandling, pris in rows:
            behandlinger[kode] = {"navn": navn_behandling, "pris": pris}
            behandling_choices.append((kode, navn_behandling))
        cur_behandlinger.close()
        conn_behandlinger.close()
    except Exception:
        behandlinger = {}
        behandling_choices = []

    # Prisene bestemmes av kombinasjonen behandling + biltype.
    price_map = {}
    try:
        conn_priser = get_conn_bestillinger()
        cur_priser = conn_priser.cursor()
        cur_priser.execute(
            """
            SELECT behandling_kode, biltype, pris
            FROM pris_tabell
            """
        )
        rows = cur_priser.fetchall()
        for kode, biltype, pris in rows:
            if kode not in price_map:
                price_map[kode] = {}
            price_map[kode][biltype.strip().lower()] = pris
        cur_priser.close()
        conn_priser.close()
    except Exception:
        price_map = {}

    form = BookingForm()
    form.tjeneste.choices = behandling_choices

    if form.validate_on_submit():

        # Valider at valgt behandling og bil faktisk finnes i de oppslagsdataene vi nettopp lastet.
        valgt_nokkel = form.tjeneste.data
        valgt_tjeneste = behandlinger.get(valgt_nokkel)
        valgt_bil = form.biltype.data.strip()
        valgt_biltype = model_type_map.get(valgt_bil)

        if not valgt_tjeneste:
            form.tjeneste.errors.append("Velg en gyldig behandling")
            return render_template(
                "bestilling.html",
                form=form,
                car_models=car_models,
                model_type_map=model_type_map,
                price_map=price_map,
            )

        if not valgt_biltype:
            form.biltype.errors.append("Velg en bil fra listen for korrekt pris")
            return render_template(
                "bestilling.html",
                form=form,
                car_models=car_models,
                model_type_map=model_type_map,
                price_map=price_map,
            )

        valgt_pris = price_map.get(valgt_nokkel, {}).get(valgt_biltype)
        if valgt_pris is None:
            form.tjeneste.errors.append("Fant ikke pris for valgt behandling og biltype")
            return render_template(
                "bestilling.html",
                form=form,
                car_models=car_models,
                model_type_map=model_type_map,
                price_map=price_map,
            )

        conn = get_conn_bestillinger()
        cur = conn.cursor()
        try:
            # Sjekk hvilke kolonner som faktisk finnes, slik at vi kan støtte eldre databaser.
            try:
                cur.execute(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                    (DB_CONFIG_BESTILLINGER['database'], 'bestillinger'),
                )
                existing_cols = {row[0] for row in cur.fetchall()}
            except Exception:
                existing_cols = set()

            # Nyere skjema bruker navn/epost/merknad.
            if {'navn', 'epost', 'merknad'}.issubset(existing_cols):
                sql = (
                    "INSERT INTO bestillinger (navn, epost, biltype, tjeneste, bestillingsdato, bestillingstid, pris, merknad, status)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                )
                params = (
                    navn,
                    session.get('email'),
                    form.biltype.data,
                    valgt_tjeneste["navn"],
                    form.bestillingsdato.data,
                    form.bestillingstid.data,
                    valgt_pris,
                    form.merknad.data,
                    'pending'
                )
                cur.execute(sql, params)
                conn.commit()

            # Eldre skjema bruker kunde_navn og obs_notat.
            elif {'kunde_navn', 'obs_notat'}.issubset(existing_cols):
                fields = ['kunde_navn', 'pakke', 'bestillingstype', 'biltype']
                vals = [navn, valgt_tjeneste.get('navn'), valgt_nokkel, form.biltype.data]
                if 'bestillingsdato' in existing_cols:
                    fields.append('bestillingsdato'); vals.append(form.bestillingsdato.data)
                if 'bestillingstid' in existing_cols:
                    fields.append('bestillingstid'); vals.append(form.bestillingstid.data)
                fields.append('pris'); vals.append(valgt_pris)
                fields.append('obs_notat'); vals.append(form.merknad.data)

                sql = f"INSERT INTO bestillinger ({','.join(fields)}) VALUES ({','.join(['%s']*len(fields))})"
                cur.execute(sql, tuple(vals))
                conn.commit()

            else:
                # Hvis skjemaet er blandet eller uventet, bygg INSERT dynamisk fra kolonnene vi kjenner.
                common = existing_cols & {'navn', 'epost', 'biltype', 'tjeneste', 'pris', 'merknad', 'bestillingsdato', 'bestillingstid', 'kunde_navn', 'obs_notat', 'bestillingstype', 'pakke'}
                if not common:
                    raise RuntimeError('Ukjent bestillinger-skjema i databasen')

                # Foretrekk nyere kolonner når de finnes, ellers fall tilbake til eldre navn.
                if 'navn' in existing_cols and 'epost' in existing_cols:
                    fields = ['navn', 'epost', 'biltype', 'tjeneste', 'pris']
                    vals = [navn, session.get('email'), form.biltype.data, valgt_tjeneste.get('navn'), valgt_pris]
                    if 'bestillingsdato' in existing_cols:
                        fields.append('bestillingsdato'); vals.append(form.bestillingsdato.data)
                    if 'bestillingstid' in existing_cols:
                        fields.append('bestillingstid'); vals.append(form.bestillingstid.data)
                    if 'merknad' in existing_cols:
                        fields.append('merknad'); vals.append(form.merknad.data)
                else:
                    
                    fields = []
                    vals = []
                    if 'kunde_navn' in existing_cols:
                        fields.append('kunde_navn'); vals.append(navn)
                    if 'pakke' in existing_cols:
                        fields.append('pakke'); vals.append(valgt_tjeneste.get('navn'))
                    if 'bestillingstype' in existing_cols:
                        fields.append('bestillingstype'); vals.append(valgt_nokkel)
                    if 'biltype' in existing_cols:
                        fields.append('biltype'); vals.append(form.biltype.data)
                    if 'bestillingsdato' in existing_cols:
                        fields.append('bestillingsdato'); vals.append(form.bestillingsdato.data)
                    if 'bestillingstid' in existing_cols:
                        fields.append('bestillingstid'); vals.append(form.bestillingstid.data)
                    if 'pris' in existing_cols:
                        fields.append('pris'); vals.append(valgt_pris)
                    if 'obs_notat' in existing_cols:
                        fields.append('obs_notat'); vals.append(form.merknad.data)

                sql = f"INSERT INTO bestillinger ({','.join(fields)}) VALUES ({','.join(['%s']*len(fields))})"
                cur.execute(sql, tuple(vals))
                conn.commit()

        except Exception as e:
            conn.rollback()
            try:
                cur.close()
                conn.close()
            except Exception:
                pass

            print('Feil ved lagring av bestilling:', e)
            form.merknad.errors.append('Kunne ikke lagre bestillingen (serverfeil). Prøv igjen senere.')
            return render_template(
                'bestilling.html',
                form=form,
                car_models=car_models,
                model_type_map=model_type_map,
                price_map=price_map,
            )
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass
        return redirect(url_for("bileier_home", bestilling_lagret="1"))

    return render_template(
        "bestilling.html",
        form=form,
        car_models=car_models,
        model_type_map=model_type_map,
        price_map=price_map,
    )


@app.route("/welcome")
def welcome_redirect():
    rolle = session.get("rolle")
    if not rolle:
        return redirect("/login")
    return redirect_to_role_home(rolle)


@app.route("/logout", methods=["POST"])
def logout():
    # Tøm session helt så neste bruker ikke arver innloggingen.
    session.clear()
    return redirect("/")


# Vaske-ekspert: Se bestillinger (kunder)
@app.route("/kunder")
def kunder():
    navn = session.get("navn")
    rolle = session.get("rolle")
    if not navn or rolle != "vaskeekspert":
        return redirect("/login")

    try:
        conn = get_conn_bestillinger()
        cur = conn.cursor()
        # Vis bare bestillinger som fortsatt venter på svar fra vaskeekspert.
        cur.execute(
            """
            SELECT bestilling_id, kunde_navn, biltype, pakke, pris, obs_notat, status
            FROM bestillinger
            WHERE COALESCE(status, 'pending') = 'pending'
            ORDER BY opprettet DESC
            """
        )
        bestillinger = []
        for row in cur.fetchall():
            bestillinger.append({
                'id': row[0],
                'navn': row[1],
                'biltype': row[2],
                'tjeneste': row[3],
                'pris': row[4],
                'merknad': row[5]
            })
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error loading bestillinger: {e}")
        bestillinger = []

    return render_template("kunder.html", bestillinger=bestillinger, name=navn)


# Vaske-ekspert: Accept eller reject bestilling
@app.route("/bestilling/<int:bestilling_id>/accept", methods=["POST"])
def accept_bestilling(bestilling_id):
    navn = session.get("navn")
    rolle = session.get("rolle")
    if not navn or rolle != "vaskeekspert":
        return redirect("/login")

    # Handlingen kommer fra skjemaet som enten sender accept eller reject.
    action = request.form.get("action")  # 'accept' or 'reject'
    if action not in ("accept", "reject"):
        return redirect("/kunder")

    try:
        conn = get_conn_bestillinger()
        cur = conn.cursor()
        if action == "accept":
            # Lås bestillingen til eksperten som tar den.
            cur.execute(
                """
                UPDATE bestillinger
                SET status = 'accepted', ekspert = %s
                WHERE bestilling_id = %s
                  AND COALESCE(status, 'pending') = 'pending'
                """,
                (navn, bestilling_id)
            )
        else:  # reject
            # Ved avslag nullstilles eksperten slik at andre ikke ser oppdraget som tatt.
            cur.execute(
                """
                UPDATE bestillinger
                SET status = 'rejected', ekspert = NULL
                WHERE bestilling_id = %s
                  AND COALESCE(status, 'pending') = 'pending'
                """,
                (bestilling_id,)
            )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error updating bestilling: {e}")

    return redirect("/kunder")


# Vaske-ekspert: Se planlagte oppdrag (accepted)
@app.route("/planlagt-oppdrag")
def planlagt_oppdrag():
    navn = session.get("navn")
    rolle = session.get("rolle")
    if not navn or rolle != "vaskeekspert":
        return redirect("/login")

    try:
        conn = get_conn_bestillinger()
        cur = conn.cursor()
        # Her vises bare oppdrag som denne eksperten selv har akseptert.
        cur.execute(
            """
            SELECT bestilling_id, kunde_navn, biltype, pakke, pris, obs_notat
            FROM bestillinger
            WHERE status = 'accepted' AND ekspert = %s
            ORDER BY opprettet ASC
            """,
            (navn,)
        )
        bestillinger = []
        for row in cur.fetchall():
            # Bygg en enkel dict som er lett å bruke i Jinja-templaten.
            bestillinger.append({
                'id': row[0],
                'navn': row[1],
                'biltype': row[2],
                'tjeneste': row[3],
                'pris': row[4],
                'merknad': row[5]
            })
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error loading planlagte oppdrag: {e}")
        bestillinger = []

    return render_template("planlagt_oppdrag.html", bestillinger=bestillinger, name=navn)


if __name__ == "__main__":
    ensure_bestillinger_table()
    ensure_bestillinger_columns()
    app.run()