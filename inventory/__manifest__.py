{
    'name': "Inventory by KSI",
    'summary': "Custom inventory operations integrated with Sales and Purchases",
    'description': """
Custom inventory module for products, warehouses, stock moves, transfers, and adjustments.
    """,
    'author': "KSI Solusi",
    'website': "https://www.ksisolusi.com",
    'category': 'Inventory',
    'version': '0.1',
    'depends': ['base', 'general', 'sales', 'purchases', 'disable_autosave'],
    'data': [
        'security/ir.model.access.csv',
        'data/menu.xml',
        'data/sequence.xml',
        'data/initial_data.xml',
        'views/views.xml',
    ],
    'license': 'LGPL-3'
}
