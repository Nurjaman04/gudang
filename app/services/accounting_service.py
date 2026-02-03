from app.models import db, Account, JournalEntry, JournalItem
from datetime import datetime

class AccountingService:
    
    @staticmethod
    def create_journal_entry(date, reference, description, lines):
        """
        Creates a double-entry journal entry.
        lines: list of tuples (account_code, debit, credit)
        """
        
        # 1. Validate Balance
        total_debit = sum([l[1] for l in lines])
        total_credit = sum([l[2] for l in lines])
        
        if abs(total_debit - total_credit) > 0.01: # Floating point tolerance
            raise ValueError(f"Journal Entry Not Balanced! Debit: {total_debit}, Credit: {total_credit}")
            
        # 2. Create Header
        je = JournalEntry(
            date=date,
            reference=reference,
            description=description
        )
        db.session.add(je)
        db.session.flush() # Get ID
        
        # 3. Create Items
        for code, debit, credit in lines:
            account = Account.query.filter_by(code=code).first()
            if not account:
                # Optional: Auto-create account? Better error for now.
                print(f"Warning: Account {code} not found. Skipping line or using Suspense?")
                continue
                
            ji = JournalItem(
                journal_entry_id=je.id,
                account_id=account.id,
                debit=debit,
                credit=credit
            )
            db.session.add(ji)
            
            # Update Account Balance (Denormalized)
            # Asset/Expense: Debit increases (+), Credit decreases (-)
            # Liab/Equity/Revenue: Credit increases (+), Debit decreases (-)
            
            if account.type in ['Asset', 'Expense']:
                account.balance += (debit - credit)
            else:
                account.balance += (credit - debit)
                
        return je

    @staticmethod
    def record_sale(reference, total_amount, cogs_amount=0):
        """
        Automated Journal for Sales:
        Dr. Cash/AR (1100/1200)
        Cr. Sales Revenue (4100)
        
        Dr. COGS (5100)
        Cr. Inventory (1300)
        """
        
        lines = [
            ('1100', total_amount, 0),       # Debit Cash
            ('4100', 0, total_amount)        # Credit Revenue
        ]
        
        if cogs_amount > 0:
            lines.append(('5100', cogs_amount, 0)) # Debit COGS
            lines.append(('1300', 0, cogs_amount)) # Credit Inventory
            
        AccountingService.create_journal_entry(
            date=datetime.utcnow(),
            reference=reference,
            description=f"Penjualan {reference}",
            lines=lines
        )

    @staticmethod
    def record_purchase(reference, amount, supplier="Supplier"):
        """
        Automated Journal for Purchase:
        Dr. Inventory (1300)
        Cr. Cash/AP (1100/2100)
        """
        lines = [
            ('1300', amount, 0),    # Debit Inventory
            ('1100', 0, amount)     # Credit Cash (Assuming Cash purchase for now)
        ]
        
        AccountingService.create_journal_entry(
            date=datetime.utcnow(),
            reference=reference,
            description=f"Pembelian Stok dari {supplier}",
            lines=lines
        )

    @staticmethod
    def record_adjustment(reference, amount, is_loss=True):
        """
        Stock Opname Adjustment
        If Loss (Stock missing):
        Dr. Expense/COGS (Adjustment Loss)
        Cr. Inventory
        
        If Gain (Found stock):
        Dr. Inventory
        Cr. Expense/COGS (Adjustment Gain - reverse expense)
        """
        
        # Use COGS account for simplicity or dedicated "Inventory Schrinkage" (6xxx)
        expense_acc = '5100' 
        inv_acc = '1300'
        
        if is_loss:
            lines = [
                (expense_acc, amount, 0),
                (inv_acc, 0, amount)
            ]
        else:
            lines = [
                (inv_acc, amount, 0),
                (expense_acc, 0, amount)
            ]
            
        AccountingService.create_journal_entry(
            date=datetime.utcnow(),
            reference=reference,
            description=f"Penyesuaian Stok (Opname)",
            lines=lines
        )
