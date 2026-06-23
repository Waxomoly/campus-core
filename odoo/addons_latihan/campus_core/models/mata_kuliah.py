from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CampusMataKuliah(models.Model):
    _name = 'campus.mata_kuliah'
    _description = 'Master Data Mata Kuliah'
    _order = 'kode_mk'
    _rec_names_search = ['name', 'kode_mk']

    kode_mk = fields.Char(string='Kode MK', required=True, copy=False, index=True)
    name = fields.Char(string='Nama Mata Kuliah', required=True)
    sks = fields.Integer(string='SKS', default=3, required=True)
    dosen_ids = fields.Many2many(
        'campus.dosen',
        relation='campus_mk_dosen_rel',
        column1='mata_kuliah_id',
        column2='dosen_id',
        string='Dosen Pengampu',
    )
    dosen_koordinator_id = fields.Many2one(
        'campus.dosen',
        string='Dosen Penanggung Jawab'
    )

    # ---- Struktur akademik ----
    fakultas_ids = fields.Many2many(
        'campus.fakultas',
        string='Fakultas'
    )

    prodi_ids = fields.Many2many(
        'campus.prodi',
        string='Program Studi',
    )

    jurusan_ids = fields.Many2many(
        'campus.jurusan',
        string='Jurusan',
    )

    # ---- Kelas ----
    kelas_ids = fields.One2many(
        'campus.kelas', 'mata_kuliah_id', string='Daftar Kelas',
    )
    kelas_count = fields.Integer(
        string='Jumlah Kelas', compute='_compute_kelas_count',
    )

    _kode_mk_unique = models.Constraint('unique(kode_mk)', 'Kode Mata Kuliah sudah ada!')
    _sks_positive = models.Constraint('CHECK(sks > 0)', 'SKS harus lebih besar dari 0!')

    @api.depends('kelas_ids')
    def _compute_kelas_count(self):
        for record in self:
            record.kelas_count = len(record.kelas_ids)

    @api.onchange('jurusan_ids')
    def _onchange_jurusan_ids(self):
        if self.jurusan_ids:
            prodi_ids = self.jurusan_ids.mapped('prodi_id')
            fakultas_ids = prodi_ids.mapped('fakultas_id')

            self.prodi_ids = [(6, 0, prodi_ids.ids)]
            self.fakultas_ids = [(6, 0, fakultas_ids.ids)]

    @api.onchange('prodi_ids')
    def _onchange_prodi_ids(self):
        if self.prodi_ids:
            fakultas_ids = self.prodi_ids.mapped('fakultas_id')

            self.fakultas_ids = [(6, 0, fakultas_ids.ids)]

    @api.constrains('sks')
    def _check_sks(self):
        for record in self:
            if record.sks <= 0:
                raise ValidationError("SKS harus lebih besar dari 0!")
