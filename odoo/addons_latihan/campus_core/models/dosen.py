from odoo import models, fields, api, Command
from odoo.exceptions import ValidationError

class CampusDosen(models.Model):
    _name = 'campus.dosen'
    _description = 'Master Data Dosen'
    _order = 'name'
    _rec_names_search = ['name', 'nip']

    nip = fields.Char(string='NIP', required=True, copy=False, index=True)
    name = fields.Char(string='Nama Dosen', required=True)
    email = fields.Char(string='Email', required=True, copy=False)
    alamat = fields.Text(string='Alamat')
    nomor_rekening = fields.Char(string='Nomor Rekening')

    user_id = fields.Many2one('res.users', string='Akun Pengguna', readonly=True, copy=False)

    # ---- Struktur akademik (hierarki kampus) ----
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

    mata_kuliah_ids = fields.Many2many(
        'campus.mata_kuliah',
        relation='campus_mk_dosen_rel',  # ← sama persis
        column1='dosen_id',
        column2='mata_kuliah_id',
        string='Mata Kuliah Diampu',
    )

    _nip_unique = models.Constraint('unique(nip)', 'NIP sudah terdaftar!')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # 1. Validasi email wajib ada
            if not vals.get('email'):
                raise ValidationError("Email wajib diisi untuk membuat akun login dosen!")

            # 2. Jika belum memiliki user_id, buatkan otomatis
            if not vals.get('user_id'):
                user_vals = {
                    'name': vals.get('name'),
                    'login': vals.get('email'),  # Email digunakan sebagai username untuk login
                    'email': vals.get('email'),
                    'password': '1234',
                    # 4. SET GRUP AKSES DOSEN (Lecturer)
                    'group_ids': [Command.link(self.env.ref('campus_core.group_campus_lecturer').id)]
                }

                # 3. Create record di res.users
                # Context no_reset_password mencegah crash jika server email belum dikonfigurasi
                new_user = self.env['res.users'].with_context(no_reset_password=True).create(user_vals)

                # 4. Pasangkan ID user baru ke field user_id dosen
                vals['user_id'] = new_user.id

        # 5. Jalankan fungsi create bawaan Odoo
        return super(CampusDosen, self).create(vals_list)


    @api.onchange('fakultas_id')
    def _onchange_fakultas_id(self):
        if self.prodi_id and self.prodi_id.fakultas_id != self.fakultas_id:
            self.prodi_id = False
            self.jurusan_id = False

    @api.onchange('prodi_id')
    def _onchange_prodi_id(self):
        if self.jurusan_id and self.jurusan_id.prodi_id != self.prodi_id:
            self.jurusan_id = False

    def write(self, vals):
        # 1. Jalankan proses update bawaan Odoo terlebih dahulu
        res = super(CampusDosen, self).write(vals)

        # 2. Cek apakah ada perubahan pada field 'email' atau 'name'
        if 'email' in vals or 'name' in vals:
            for record in self:
                # 3. Jika dosen ini sudah punya akun Odoo, update akunnya
                if record.user_id:
                    user_update = {}
                    if 'name' in vals:
                        user_update['name'] = vals['name']
                    if 'email' in vals:
                        user_update['login'] = vals['email']  # Username login
                        user_update['email'] = vals['email']  # Email notifikasi

                    # Gunakan sudo() agar proses update tidak terhalang hak akses
                    record.user_id.sudo().write(user_update)

        return res
