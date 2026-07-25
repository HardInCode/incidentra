"""Contact form lab — intentionally missing CSRF protection (capstone demo)."""
from flask import Blueprint, g, redirect, render_template, request, url_for

forms_bp = Blueprint('forms', __name__)


@forms_bp.route('/forms', methods=['GET', 'POST'])
def forms():
    error = request.args.get('error', '')
    success = request.args.get('success', '')

    if request.method == 'POST':
        # Lab: no csrf_token field in the HTML form — any POST without it is rejected.
        if not request.form.get('csrf_token'):
            g.log_extra = 'error=CSRF+token+missing'
            return render_template(
                'forms.html',
                error='CSRF token missing — request rejected.',
                name=request.form.get('name', ''),
                email=request.form.get('email', ''),
                message=request.form.get('message', ''),
            ), 403

        return redirect(url_for('forms.forms', success='Thanks — your message was received.'))

    return render_template(
        'forms.html',
        error=error,
        success=success,
        name='',
        email='',
        message='',
    )
