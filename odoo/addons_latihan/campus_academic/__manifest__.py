{
    'name': 'Campus Academic',
    'version': '19.0.1.0.0',
    'summary': 'Extension module: Transkrip Nilai, IP/IPK, Status Kelulusan',
    'category': 'Education',
    'author': 'Shella',
    'depends': ['campus_core'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'report/transkrip_report.xml',
        'views/transkrip_views.xml',
        'views/mahasiswa_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
