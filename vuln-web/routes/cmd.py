import subprocess

from flask import Blueprint, render_template, request

from config import CMD_TIMEOUT_SEC, VULN_UNSAFE_CMD

cmd_bp = Blueprint('cmd', __name__)


@cmd_bp.route('/cmd')
def cmd():
    cmd_input = request.args.get('cmd', '')
    output = ''
    mode = 'simulated'

    if cmd_input:
        if VULN_UNSAFE_CMD:
            mode = 'unsafe'
            try:
                completed = subprocess.run(
                    cmd_input,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=CMD_TIMEOUT_SEC,
                    cwd=None,
                )
                parts = []
                if completed.stdout:
                    parts.append(completed.stdout)
                if completed.stderr:
                    parts.append(completed.stderr)
                output = ''.join(parts) or f'(exit code {completed.returncode})'
            except subprocess.TimeoutExpired:
                output = f'Command timed out after {CMD_TIMEOUT_SEC}s'
            except Exception as e:
                output = str(e)
        else:
            output = (
                f'[Simulated] Would execute: {cmd_input}\n'
                'Enable VULN_UNSAFE_CMD=1 in .env for real execution (lab only).'
            )

    return render_template(
        'cmd.html',
        cmd_input=cmd_input,
        output=output,
        cmd_mode=mode,
    )
