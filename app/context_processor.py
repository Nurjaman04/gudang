from flask import session
from app.models import Product

def inject_notifications():
    def get_notifications():
        # Only check for specific roles
        allowed_roles = ['admin', 'kepala_gudang', 'kepala_divisi']
        user_role = session.get('role')
        
        if not user_role or user_role not in allowed_roles:
            return {'count': 0, 'items': []}

        # Query Low Stock Products
        low_stock_items = Product.query.filter(Product.stock_quantity <= Product.min_stock_threshold).all()
        
        return {
            'count': len(low_stock_items),
            'alerts': low_stock_items
        }

    return dict(notifications=get_notifications())
