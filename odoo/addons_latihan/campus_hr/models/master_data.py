from odoo import models, fields, api


class CampusOrganisasiTipe(models.Model):
    _name = 'campus.organisasi.tipe'
    _description = 'Master Data Tipe Organisasi'
    _order = 'name'
    _rec_names_search = ['name', 'kode']

    kode = fields.Char(string='Kode', copy=False, index=True)
    name = fields.Char(string='Nama Tipe Organisasi', required=True)
    deskripsi = fields.Text(string='Deskripsi')
    jabatan_ids = fields.One2many(
        'campus.jabatan', 'tipe_id', string='Jabatan Khusus',
    )

    _name_unique = models.Constraint('unique(name)', 'Tipe organisasi sudah ada!')


class CampusJabatan(models.Model):
    _name = 'campus.jabatan'
    _description = 'Master Data Jabatan Organisasi'
    _order = 'sequence, name'
    _rec_names_search = ['name']

    sequence = fields.Integer(string='Urutan', default=10)
    name = fields.Char(string='Nama Jabatan', required=True)
    tipe_id = fields.Many2one(
        'campus.organisasi.tipe', string='Tipe Organisasi', ondelete='cascade',
        help='Kosongkan bila jabatan berlaku untuk SEMUA tipe organisasi.',
    )
    is_umum = fields.Boolean(
        string='Berlaku Umum', compute='_compute_is_umum', store=True,
        help='True bila jabatan tidak terikat pada tipe tertentu.',
    )

    @api.depends('tipe_id')
    def _compute_is_umum(self):
        for record in self:
            record.is_umum = not record.tipe_id

    @api.depends('name', 'tipe_id')
    def _compute_display_name(self):
        for record in self:
            if record.tipe_id:
                record.display_name = "%s (%s)" % (record.name, record.tipe_id.name)
            else:
                record.display_name = record.name


class CampusJabatanPanitia(models.Model):
    _name = 'campus.jabatan.panitia'
    _description = 'Master Data Jabatan Kepanitiaan'
    _order = 'sequence, name'
    _rec_names_search = ['name']

    sequence = fields.Integer(string='Urutan', default=10)
    name = fields.Char(string='Nama Jabatan Kepanitiaan', required=True)
    is_bph = fields.Boolean(
        string='Jabatan BPH',
        help='Centang bila jabatan ini untuk divisi BPH (Badan Pengurus Harian), '
             'mis. Wakil Ketua/Sekretaris/Bendahara.',
    )

    _name_unique = models.Constraint('unique(name)', 'Jabatan kepanitiaan sudah ada!')


class CampusDivisi(models.Model):
    _name = 'campus.divisi'
    _description = 'Master Data Divisi Kepanitiaan'
    _order = 'sequence, name'
    _rec_names_search = ['name']

    sequence = fields.Integer(string='Urutan', default=10)
    name = fields.Char(string='Nama Divisi', required=True)
    deskripsi = fields.Text(string='Deskripsi')
    is_bph = fields.Boolean(
        string='Divisi BPH',
        help='Centang bila ini divisi BPH (Badan Pengurus Harian). '
             'Hanya jabatan BPH yang bisa dipilih untuk divisi ini.',
    )

    _name_unique = models.Constraint('unique(name)', 'Divisi sudah ada!')
