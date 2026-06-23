from odoo import models, fields, api

# Hierarki struktur kampus: Fakultas -> Program Studi -> Jurusan
# - 1 Fakultas memiliki banyak Program Studi
# - 1 Program Studi memiliki banyak Jurusan
# - Jurusan adalah level paling bawah (anak dari Prodi)


class CampusFakultas(models.Model):
    _name = 'campus.fakultas'
    _description = 'Master Data Fakultas'
    _order = 'name'
    _rec_names_search = ['name', 'kode']

    kode = fields.Char(string='Kode Fakultas', required=True, copy=False, index=True)
    name = fields.Char(string='Nama Fakultas', required=True)
    prodi_ids = fields.One2many(
        'campus.prodi', 'fakultas_id', string='Daftar Program Studi',
    )
    prodi_count = fields.Integer(
        string='Jumlah Prodi', compute='_compute_counts',
    )
    jurusan_count = fields.Integer(
        string='Jumlah Jurusan', compute='_compute_counts',
    )

    _kode_unique = models.Constraint('unique(kode)', 'Kode Fakultas sudah ada!')

    @api.depends('prodi_ids', 'prodi_ids.jurusan_ids')
    def _compute_counts(self):
        for record in self:
            record.prodi_count = len(record.prodi_ids)
            record.jurusan_count = len(record.prodi_ids.mapped('jurusan_ids'))


class CampusProdi(models.Model):
    _name = 'campus.prodi'
    _description = 'Master Data Program Studi (Prodi)'
    _order = 'name'
    _rec_names_search = ['name', 'kode']

    kode = fields.Char(string='Kode Prodi', required=True, copy=False, index=True)
    name = fields.Char(string='Nama Program Studi', required=True)
    jenjang = fields.Selection([
        ('d3', 'D3'),
        ('d4', 'D4'),
        ('s1', 'S1'),
        ('s2', 'S2'),
        ('s3', 'S3'),
    ], string='Jenjang', default='s1', required=True)
    fakultas_id = fields.Many2one(
        'campus.fakultas', string='Fakultas',
        required=True, ondelete='restrict', index=True,
    )
    jurusan_ids = fields.One2many(
        'campus.jurusan', 'prodi_id', string='Daftar Jurusan',
    )
    jurusan_count = fields.Integer(
        string='Jumlah Jurusan', compute='_compute_jurusan_count',
    )

    _kode_unique = models.Constraint('unique(kode)', 'Kode Prodi sudah ada!')

    @api.depends('jurusan_ids')
    def _compute_jurusan_count(self):
        for record in self:
            record.jurusan_count = len(record.jurusan_ids)


class CampusJurusan(models.Model):
    _name = 'campus.jurusan'
    _description = 'Master Data Jurusan'
    _order = 'name'
    _rec_names_search = ['name', 'kode']

    kode = fields.Char(string='Kode Jurusan', required=True, copy=False, index=True)
    name = fields.Char(string='Nama Jurusan', required=True)
    prodi_id = fields.Many2one(
        'campus.prodi', string='Program Studi',
        required=True, ondelete='restrict', index=True,
    )
    fakultas_id = fields.Many2one(
        'campus.fakultas', string='Fakultas',
        related='prodi_id.fakultas_id', store=True, readonly=True,
    )

    _kode_unique = models.Constraint('unique(kode)', 'Kode Jurusan sudah ada!')
