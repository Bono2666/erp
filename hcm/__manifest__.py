{
    'name': "Human Capital Management by KSI",

    'summary': "Human Capital Management Module",

    'description': """
Human Capital Management (HCM) Module
- Employee Master Data
- Position & Organization Structure
- Family, Education, Certificate, Training
- Document Repository
    """,

    'author': "KSI Solusi",
    'website': "https://www.ksisolusi.com",

    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'general', 'disable_autosave'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/views.xml',
        'data/sequence.xml',
        'data/menu.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'hcm/static/src/js/org_structure.js',
            'hcm/static/src/xml/org_structure.xml',
        ],
    },

    'license': 'LGPL-3',
}
