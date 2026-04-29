from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.fields import DateField, TimeField
from wtforms.validators import DataRequired, EqualTo, ValidationError
from datetime import time as dtime

class RegisterForm(FlaskForm):
    role = SelectField(
        "Brukertype",
        choices=[("vaskeekspert", "Vaskeekspert"), ("bileier", "Bileier")],
        validators=[DataRequired()],
    )
    name = StringField("Navn", validators=[DataRequired()])
    email = StringField("E-post", validators=[DataRequired()])
    password = PasswordField("Passord", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Bekreft passord",
        validators=[DataRequired(), EqualTo("password", message="Passordene matcher ikke")],
    )
    submit = SubmitField("Registrer")

class LoginForm(FlaskForm):
    email = StringField("E-post", validators=[DataRequired()])
    password = PasswordField("Passord", validators=[DataRequired()])
    submit = SubmitField("Logg inn")


class BookingForm(FlaskForm):
    tjeneste = SelectField("Type vask", validators=[DataRequired()])
    biltype = StringField("Hva slags bil skal behandles?", validators=[DataRequired()])
    bestillingsdato = DateField(
        "Dato",
        format="%Y-%m-%d",
        validators=[DataRequired()],
    )
    bestillingstid = TimeField(
        "Klokkeslett",
        format="%H:%M",
        validators=[DataRequired()],
    )
    merknad = TextAreaField("Noe vi bør vite?", validators=[DataRequired()])
    submit = SubmitField("Send bestilling")

    def validate_bestillingstid(self, field):
        t = field.data
        if t is None:
            return
        min_time = dtime(10, 0)
        max_time = dtime(18, 0)
        if t < min_time or t > max_time:
            raise ValidationError("Velg et klokkeslett mellom 10:00 og 18:00.")
        if t.minute not in (0, 30):
            raise ValidationError("Velg minutter 00 eller 30.")
