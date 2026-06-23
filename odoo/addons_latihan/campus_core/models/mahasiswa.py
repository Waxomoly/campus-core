from datetime import date

from odoo import models, fields, api
from odoo.exceptions import ValidationError

# range tahun untuk dropdown angkatan & semester aktif
tahun_awal_angkatan = 2015
tahun_awal_semester = 2024


class CampusMahasiswa(models.Model):
    _name = 'campus.mahasiswa'
    _description = 'Master Data Mahasiswa'
    _order = 'nim'
    _rec_names_search = ['name', 'nim']

    nim = fields.Char(string='NIM', required=True, copy=False, index=True)
    name = fields.Char(string='Nama Mahasiswa', required=True)
    email = fields.Char(string='Email', required=True, copy=False)

    # mengaitkan mahasiswa dengan akun login
    user_id = fields.Many2one('res.users', string='User Account', readonly=True, copy=False)

    tempat_lahir = fields.Char(string='Tempat Lahir')
    tanggal_lahir = fields.Date(string='Tanggal Lahir')
    jenis_kelamin = fields.Selection([
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ], string='Jenis Kelamin')
    alamat = fields.Text(string='Alamat')

    angkatan = fields.Selection(
        selection='_get_angkatan_selection', string='Angkatan',
        help='Tahun masuk mahasiswa.',
    )
    semester_aktif = fields.Selection(
        selection='_get_semester_aktif_selection', string='Semester Aktif',
        default=lambda self: self._default_semester_aktif(),
        help='Periode semester berjalan, mis. Semester Gasal 2025/2026.',
    )
    ipk = fields.Float(string='IPK', digits=(3, 2))

    fakultas_id = fields.Many2one(
        'campus.fakultas', string='Fakultas',
        ondelete='restrict', index=True,
    )
    prodi_id = fields.Many2one(
        'campus.prodi', string='Program Studi',
        ondelete='restrict', index=True,
        domain="[('fakultas_id', '=', fakultas_id)]",
    )
    jurusan_id = fields.Many2one(
        'campus.jurusan', string='Jurusan',
        ondelete='restrict', index=True,
        domain="[('prodi_id', '=', prodi_id)]",
    )

    status = fields.Selection([
        ('aktif', 'Aktif'),
        ('non_aktif', 'Non-Aktif'),
        ('lulus', 'Lulus'),
        ('cuti', 'Cuti'),
    ], string='Status', default='aktif', required=True)

    total_sks_lulus = fields.Integer(
        string='Total SKS Lulus', default=0,
        help='Total SKS yang sudah diselesaikan (lulus). '
             'Otomatis terisi bila modul Academic terpasang.',
    )
    status_kelulusan = fields.Selection([
        ('belum', 'Belum Lulus'),
        ('lulus', 'Lulus'),
    ], string='Status Kelulusan', default='belum', required=True)

    _sql_constraints = [
        ('nim_unique', 'unique(nim)', 'NIM sudah terdaftar! Sistem tidak mengizinkan duplikasi NIM.'),
        ('email_unique', 'unique(email)',
         'Email ini sudah digunakan oleh mahasiswa lain! Silakan gunakan email yang berbeda.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('email'):
                raise ValidationError("Email wajib diisi untuk membuat akun login!")

            if not vals.get('user_id'):
                user_vals = {
                    'name': vals.get('name'),
                    'login': vals.get('email'),
                    'email': vals.get('email'),
                    # Password awal default = 1234 (dianjurkan diganti nanti)
                    'password': '1234',
                    # Beri role "Mahasiswa" agar akun bisa mengakses fitur campus
                    'group_ids': [(4, self.env.ref('campus_core.group_campus_student').id)],
                }
                new_user = self.env['res.users'].with_context(no_reset_password=True).create(user_vals)

                vals['user_id'] = new_user.id

        return super(CampusMahasiswa, self).create(vals_list)

    @api.model
    def _get_angkatan_selection(self):
        tahun_sekarang = date.today().year
        return [
            (str(tahun), str(tahun))
            for tahun in range(tahun_awal_angkatan, tahun_sekarang + 2)
        ]

    @api.model
    def _get_semester_aktif_selection(self):
        tahun_sekarang = date.today().year
        opsi = []
        for tahun in range(tahun_awal_semester, tahun_sekarang + 3):
            tahun_ajaran = "%d/%d" % (tahun, tahun + 1)
            opsi.append((
                "Gasal %s" % tahun_ajaran,
                "Gasal %s" % tahun_ajaran,
            ))
            opsi.append((
                "Genap %s" % tahun_ajaran,
                "Genap %s" % tahun_ajaran,
            ))
        return opsi

    @api.model
    def _default_semester_aktif(self):
        """Semester aktif berjalan, ter-generate otomatis dari tanggal hari ini."""
        today = date.today()
        if today.month >= 8:
            return "Gasal %d/%d" % (today.year, today.year + 1)
        if today.month == 1:
            return "Gasal %d/%d" % (today.year - 1, today.year)
        # Genap 2025/2026
        return "Genap %d/%d" % (today.year - 1, today.year)

    @api.onchange('fakultas_id')
    def _onchange_fakultas_id(self):
        if self.prodi_id and self.prodi_id.fakultas_id != self.fakultas_id:
            self.prodi_id = False
            self.jurusan_id = False

    @api.onchange('prodi_id')
    def _onchange_prodi_id(self):
        if self.jurusan_id and self.jurusan_id.prodi_id != self.prodi_id:
            self.jurusan_id = False

    @api.constrains('ipk')
    def _check_ipk(self):
        for record in self:
            if record.ipk < 0.0 or record.ipk > 4.0:
                raise ValidationError(
                    "IPK harus berada di rentang 0.00 - 4.00! "
                    "(IPK %s saat ini: %.2f)" % (record.name, record.ipk)
                )
