from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo

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
