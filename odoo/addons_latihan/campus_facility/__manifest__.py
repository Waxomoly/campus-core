{
    'name': 'Campus Facility',
    'version': '19.0.1.0.0',
    'summary': 'Extension module: Booking Ruangan, Reservasi Fasilitas, Maintenance',
    'category': 'Education',
    'author': 'Kelly',
    'depends': ['campus_core'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'report/booking_report.xml',
        'views/facility_views.xml',
        'views/booking_views.xml',
        'views/mahasiswa_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
