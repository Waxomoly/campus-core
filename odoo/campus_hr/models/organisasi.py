from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError


class CampusOrganisasi(models.Model):
    _name = 'campus.organisasi'
    _description = 'Organisasi Mahasiswa'
    _order = 'name'

    kode = fields.Char(string='Kode Organisasi', required=True, copy=False, index=True)
    name = fields.Char(string='Nama Organisasi', required=True)
    tipe_id = fields.Many2one(
        'campus.organisasi.tipe', string='Tipe Organisasi',
        ondelete='restrict', index=True,
    )
    deskripsi = fields.Text(string='Deskripsi')
    pembina_id = fields.Many2one(
        'campus.dosen', string='Dosen Pembina',
        ondelete='restrict', index=True,
        help='Dosen pembina yang bertanggung jawab atas organisasi ini '
             'dan proposal kegiatannya.',
    )
    ketua_id = fields.Many2one(
        'campus.mahasiswa', string='Ketua Umum',
        ondelete='restrict',
    )
    ketua_jurusan_id = fields.Many2one(
        'campus.jurusan', string='Jurusan Ketua Umum',
        related='ketua_id.jurusan_id', store=True, readonly=True,
    )
    anggota_ids = fields.One2many(
        'campus.organisasi.anggota', 'organisasi_id', string='Struktur Organisasi',
    )
    proposal_ids = fields.One2many(
        'campus.proposal', 'organisasi_id', string='Proposal Kegiatan',
    )
    jumlah_anggota = fields.Integer(
        string='Jumlah Anggota', compute='_compute_jumlah_anggota', store=True,
    )
    proposal_count = fields.Integer(
        string='Jumlah Proposal', compute='_compute_proposal_count',
    )
    state = fields.Selection([
        ('aktif', 'Aktif'),
        ('nonaktif', 'Non-Aktif'),
    ], string='Status', default='aktif', required=True, readonly=True, copy=False)

    _kode_unique = models.Constraint('unique(kode)', 'Kode organisasi sudah ada!')

    @api.depends('anggota_ids')
    def _compute_jumlah_anggota(self):
        for record in self:
            record.jumlah_anggota = len(record.anggota_ids)

    @api.depends('proposal_ids')
    def _compute_proposal_count(self):
        for record in self:
            record.proposal_count = len(record.proposal_ids)

    def _ensure_lecturer(self):
        if not self.env.user.has_group('campus_core.group_campus_lecturer'):
            raise AccessError(
                "Hanya Dosen (Lecturer) yang dapat mengaktifkan atau "
                "menonaktifkan organisasi. Mahasiswa tidak memiliki akses ini."
            )

    def action_set_nonaktif(self):
        self._ensure_lecturer()
        self.write({'state': 'nonaktif'})

    def action_set_aktif(self):
        self._ensure_lecturer()
        self.write({'state': 'aktif'})

    def action_view_proposal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proposal Kegiatan',
            'res_model': 'campus.proposal',
            'view_mode': 'list,form',
            'domain': [('organisasi_id', '=', self.id)],
            'context': {'default_organisasi_id': self.id},
        }


class CampusOrganisasiAnggota(models.Model):
    _name = 'campus.organisasi.anggota'
    _description = 'Struktur Organisasi / Anggota'

    organisasi_id = fields.Many2one(
        'campus.organisasi', string='Organisasi', required=True, ondelete='cascade',
    )
    mahasiswa_id = fields.Many2one(
        'campus.mahasiswa', string='Mahasiswa', required=True, ondelete='restrict',
    )
    jabatan_id = fields.Many2one(
        'campus.jabatan', string='Jabatan', ondelete='restrict',
    )

    @api.constrains('mahasiswa_id', 'organisasi_id')
    def _check_duplicate_member(self):
        for record in self:
            duplikat = self.search_count([
                ('id', '!=', record.id),
                ('organisasi_id', '=', record.organisasi_id.id),
                ('mahasiswa_id', '=', record.mahasiswa_id.id),
            ])
            if duplikat:
                raise ValidationError(
                    "Mahasiswa sudah terdaftar sebagai anggota organisasi ini!"
                )
