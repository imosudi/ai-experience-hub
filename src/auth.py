from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, session, flash, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from src.logger import logger

auth_bp = Blueprint('auth', __name__)

class LoginForm(FlaskForm):
    """CSRF-protected login form for mock token entry."""
    token = StringField('Demo Token', validators=[DataRequired(message="Token is required")], render_kw={"placeholder": "Enter MUSE-SPARK-DEMO-2026"})
    submit = SubmitField('Verify Token')


def login_required(f):
    """
    Decorator to protect views. Redirects unauthorized users
    to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'auth_token' not in session:
            logger.warning(f"Unauthenticated request to protected route: {request.path}")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles session login using the configurable demo token."""
    if 'auth_token' in session:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    next_url = request.args.get('next') or url_for('main.dashboard')

    if form.validate_on_submit():
        entered_token = form.token.data.strip()
        required_token = current_app.config.get('DEMO_TOKEN', 'MUSE-SPARK-DEMO-2026')

        if entered_token == required_token:
            session.permanent = True
            session['auth_token'] = entered_token
            logger.info("Mock authentication token verified. Session started.")
            flash("Welcome to Muse Spark Explorer! Session authenticated successfully.", "success")
            return redirect(next_url)
        else:
            logger.warning("Failed mock authentication login attempt.")
            flash("Invalid authentication token. Please try again.", "danger")

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
def logout():
    """Ends the session and logs the user out."""
    session.pop('auth_token', None)
    logger.info("Session destroyed. User logged out.")
    flash("You have been logged out of your session.", "info")
    return redirect(url_for('auth.login'))
