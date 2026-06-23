{
    'name': 'Campus Attendance',
    'version': '19.0.1.0.0',
    'summary': 'Extension module: Absensi Mahasiswa, Persentase Kehadiran, Warning',
    'category': 'Education',
    'author': 'Clar',
    'depends': ['campus_core'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'report/attendance_report.xml',
        'views/attendance_views.xml',
        'views/mahasiswa_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
