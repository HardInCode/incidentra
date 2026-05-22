from routes.api import api_bp
from routes.auth import auth_bp
from routes.cart import cart_bp
from routes.cmd import cmd_bp
from routes.files import files_bp
from routes.main import main_bp
from routes.profile import profile_bp
from routes.shop import shop_bp


def register_blueprints(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(cmd_bp)
    app.register_blueprint(api_bp)
