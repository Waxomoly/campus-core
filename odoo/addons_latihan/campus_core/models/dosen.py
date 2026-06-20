from odoo import models, fields, api


class CampusDosen(models.Model):
    _name = 'campus.dosen'
    _description = 'Master Data Dosen'
    _order = 'name'
    _rec_names_search = ['name', 'nip']

    nip = fields.Char(string='NIP', required=True, copy=False, index=True)
    name = fields.Char(string='Nama Dosen', required=True)

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

    @api.onchange('fakultas_id')
    def _onchange_fakultas_id(self):
        if self.prodi_id and self.prodi_id.fakultas_id != self.fakultas_id:
            self.prodi_id = False
            self.jurusan_id = False

    @api.onchange('prodi_id')
    def _onchange_prodi_id(self):
        if self.jurusan_id and self.jurusan_id.prodi_id != self.prodi_id:
            self.jurusan_id = False
