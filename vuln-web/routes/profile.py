import os

from flask import Blueprint, redirect, render_template, request, url_for

from config import SAFE_FILES_DIR

profile_bp = Blueprint('profile', __name__)

AVATAR_DIR = 'avatars'


@profile_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    name = request.args.get('name', request.form.get('name', 'Guest'))
    avatar_message = ''

    if request.method == 'POST' and 'avatar' in request.files:
        upload = request.files['avatar']
        if upload and upload.filename:
            # CTF-style profile picture: no extension whitelist, no size cap (lab only)
            dest_dir = os.path.join(SAFE_FILES_DIR, AVATAR_DIR)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, upload.filename)
            upload.save(dest)
            avatar_message = f'Profile photo saved as: {upload.filename}'
            return redirect(url_for('profile.profile', name=name, avatar_msg=avatar_message))

    avatar_message = request.args.get('avatar_msg', avatar_message)

    return render_template(
        'profile.html',
        name=name,
        avatar_message=avatar_message,
    )
