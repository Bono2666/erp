{
    'name': "General by KSI",

    'summary': "General Master Table",

    'description': """
General Master Table
    """,

    'author': "KSI Solusi",
    'website': "https://www.ksisolusi.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Technical',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'disable_autosave'],
    'uninstall_hook': 'uninstall_hook_cleanup_users',

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'data/home.xml',
        'views/splash.xml',
        'views/views.xml',
        'data/menu.xml',
        'data/sequence.xml',
        'data/logo.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'general/static/src/css/splash_screen.css',
            'general/static/src/js/splash_screen.js',
            'general/static/src/xml/splash_screen.xml',
        ],
    },

    'license': 'LGPL-3',
}
