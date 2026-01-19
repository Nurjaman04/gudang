from flask import Flask
from app.config import Config
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        # --- 1. IMPORT BLUEPRINT (Pastikan nama file benar) ---
        from app.controllers.auth_controller import auth_bp
        from app.controllers.inventory_controller import inventory_bp
        from app.controllers.sales_controller import sales_bp
        from app.controllers.web_controller import web_bp  # <--- JANGAN HILANG

        # --- 2. REGISTER BLUEPRINT (Agar Flask tahu halaman ini ada) ---
        app.register_blueprint(auth_bp)
        app.register_blueprint(inventory_bp)
        app.register_blueprint(sales_bp)
        app.register_blueprint(web_bp)  # <--- JANGAN HILANG

        # Context Processor untuk Notifikasi (Biarkan jika sudah ada)
        # Context Processor untuk Notifikasi
        from app.context_processor import inject_notifications
        app.context_processor(inject_notifications)

        db.create_all()

    return app