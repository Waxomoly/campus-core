{
    'name': 'Integrated Campus Management System - Core',
    'version': '19.0.2.0.0',
    'summary': 'Core module untuk sistem informasi akademik kampus',
    'description': """
Integrated Campus Management System - Core
==========================================
Modul inti untuk pengelolaan data akademik kampus:
- Master Data Struktur Kampus (Fakultas -> Jurusan -> Prodi)
- Master Data Mahasiswa
- Master Data Dosen
- Master Data Mata Kuliah & Kelas (jadwal + kuota)
- KRS / Enrollment Mahasiswa dengan:
  * Pemilihan kelas berbasis kuota (FCFS / rebutan)
  * Validasi jadwal bentrok & batas 24 SKS
  * Workflow Student (submit) & Lecturer (process)
  * Status per mata kuliah (pending/approved/rejected)
    """,
    'category': 'Education',
    'author': 'Kelompok Kampus',
    'depends': ['base'],
    'data': [
        'security/campus_security.xml',
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/struktur_views.xml',
        'views/mahasiswa_views.xml',
        'views/dosen_views.xml',
        'views/mata_kuliah_views.xml',
        'views/kelas_views.xml',
        'views/krs_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
