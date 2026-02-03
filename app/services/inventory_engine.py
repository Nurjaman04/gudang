from datetime import datetime
from app.models import db, Product, Batch, Transaction, BatchTransaction
from sqlalchemy import func

class SmartInventoryEngine:
    
    @staticmethod
    def process_inbound(product_id, quantity, cost_price, expiry_date=None, auto_commit=True):
        """
        Smart Inbound: Creates a new batch correctly.
        """
        product = Product.query.get(product_id)
        if not product:
            raise ValueError("Product not found")

        # Create Batch
        batch_number = f"BATCH-{datetime.now().strftime('%Y%m%d')}-{product_id}-{int(datetime.now().timestamp())}"
        new_batch = Batch(
            product_id=product_id,
            batch_number=batch_number,
            initial_quantity=quantity,
            current_quantity=quantity,
            cost_price=cost_price,
            expiry_date=expiry_date
        )
        
        db.session.add(new_batch)
        if auto_commit:
            db.session.commit()
            
        return new_batch

    @staticmethod
    def process_outbound_fifo(product_id, quantity_needed, transaction_id=None):
        """
        Smart Outbound (FIFO): Automatically picks older batches first.
        Returns: Allocated Batches List
        """
        # Get batches ordered by created_at (FIFO)
        batches = Batch.query.filter(
            Batch.product_id == product_id,
            Batch.current_quantity > 0
        ).order_by(Batch.expiry_date.asc().nulls_last(), Batch.created_at.asc()).all()

        allocated = []
        remaining_qty = quantity_needed

        for batch in batches:
            if remaining_qty <= 0:
                break
            
            qty_taken = min(batch.current_quantity, remaining_qty)
            
            # Update Batch
            batch.current_quantity -= qty_taken
            remaining_qty -= qty_taken
            
            # Record Allocation
            allocated.append({
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'quantity': qty_taken,
                'cost': batch.cost_price
            })
            
            # Link to Transaction if ID provided
            if transaction_id:
                bt = BatchTransaction(
                    transaction_id=transaction_id,
                    batch_id=batch.id,
                    quantity=qty_taken
                )
                db.session.add(bt)
        
        if remaining_qty > 0:
            # Force Allocation (Negative Stock on newest batch or error? For now, allow partial and let main logic handle shortage)
            # ideally we shouldn't reach here if we checked total stock first
            pass

        return allocated

    @staticmethod
    def calculate_valuation_fifo():
        """
        Real-time Stock Valuation based on actual remaining batches.
        More accurate than Average Cost.
        """
        valuation = db.session.query(
            func.sum(Batch.current_quantity * Batch.cost_price)
        ).scalar()
        return valuation or 0

    @staticmethod
    def get_stock_ageing_report():
        """
        Returns products categorized by age of stock (Days in Inventory).
        """
        today = datetime.utcnow()
        batches = Batch.query.filter(Batch.current_quantity > 0).all()
        
        ageing_data = []
        for b in batches:
            age_days = (today - b.created_at).days
            category = 'Fresh (<30 days)'
            if 30 <= age_days < 60: category = 'Aging (30-60 days)'
            elif 60 <= age_days < 90: category = 'Old (60-90 days)'
            elif age_days >= 90: category = 'Obsolete (>90 days)'
            
            ageing_data.append({
                'product': b.product.name,
                'batch': b.batch_number,
                'qty': b.current_quantity,
                'age_days': age_days,
                'category': category,
                'expiry': b.expiry_date
            })
            
        return ageing_data
