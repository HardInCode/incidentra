import os

from flask import Blueprint, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from config import SAFE_FILES_DIR, VULN_UNSAFE_UPLOAD

files_bp = Blueprint('files', __name__)

UPLOAD_SUBDIR = 'uploads'


def _upload_dir():
    path = os.path.join(SAFE_FILES_DIR, UPLOAD_SUBDIR)
    os.makedirs(path, exist_ok=True)
    return path


def _save_upload(upload) -> tuple[str, str]:
    """Save uploaded file; returns (message, saved_path)."""
    if not upload or not upload.filename:
        return '', ''

    if VULN_UNSAFE_UPLOAD:
        raw_name = upload.filename.replace('\\', '/')
        dest = os.path.normpath(os.path.join(_upload_dir(), raw_name))
        safe_root = os.path.abspath(SAFE_FILES_DIR)
        if not os.path.abspath(dest).startswith(safe_root):
            dest = os.path.normpath(os.path.join(os.getcwd(), raw_name))
        os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
        upload.save(dest)
        return f'[UNSAFE] Saved to: {dest}', dest

    safe_name = secure_filename(upload.filename) or 'upload.bin'
    dest = os.path.join(_upload_dir(), safe_name)
    upload.save(dest)
    return f'Uploaded: {safe_name}', dest


def _list_safe_files():
    names = []
    if os.path.isdir(SAFE_FILES_DIR):
        for name in sorted(os.listdir(SAFE_FILES_DIR)):
            full = os.path.join(SAFE_FILES_DIR, name)
            if os.path.isfile(full):
                names.append(name)
    return names


def _list_uploads():
    upload_path = _upload_dir()
    if not os.path.isdir(upload_path):
        return []
    return sorted(
        n for n in os.listdir(upload_path)
        if os.path.isfile(os.path.join(upload_path, n))
    )


def _read_file_request(filename: str) -> tuple[str, str]:
    if not filename:
        return '', ''

    os.makedirs(SAFE_FILES_DIR, exist_ok=True)

    if os.path.isabs(filename) or (len(filename) > 1 and filename[1] == ':'):
        target = filename
    else:
        target = os.path.join(SAFE_FILES_DIR, filename.replace('../', ''))

    try:
        if os.path.isfile(target):
            with open(target, 'r', encoding='utf-8', errors='replace') as f:
                return f.read(), target
        return f'[Simulated] Would read: {filename}', target
    except Exception as e:
        return str(e), target


@files_bp.route('/files', methods=['GET', 'POST'])
def files():
    message = ''
    if request.method == 'POST' and 'file' in request.files:
        message, _dest = _save_upload(request.files['file'])
        if message:
            return redirect(url_for('files.files', msg=message))

    message = request.args.get('msg', message)
    filename = request.args.get('file', '')
    content = ''
    if filename:
        content, _resolved = _read_file_request(filename)

    return render_template(
        'files.html',
        filename=filename,
        content=content,
        safe_files=_list_safe_files(),
        uploads=_list_uploads(),
        message=message,
    )
