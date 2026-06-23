from odoo import models, fields, api


class CampusMahasiswa(models.Model):
    _inherit = 'campus.mahasiswa'

    keanggotaan_ids = fields.One2many(
        'campus.organisasi.anggota', 'mahasiswa_id', string='Keanggotaan Organisasi',
    )
    ketua_organisasi_ids = fields.One2many(
        'campus.organisasi', 'ketua_id', string='Ketua Organisasi',
    )
    organisasi_count = fields.Integer(
        string='Jumlah Organisasi', compute='_compute_organisasi_count',
    )
    sudah_berorganisasi = fields.Boolean(
        string='Sudah Berorganisasi', compute='_compute_sudah_berorganisasi',
        store=True,
        help='True bila mahasiswa sudah tergabung di sebuah organisasi '
             '(sebagai anggota maupun ketua). Dipakai untuk menyaring pilihan '
             'agar satu mahasiswa tidak masuk lebih dari satu organisasi.',
    )

    @api.depends('keanggotaan_ids')
    def _compute_organisasi_count(self):
        for record in self:
            record.organisasi_count = len(record.keanggotaan_ids.mapped('organisasi_id'))

    @api.depends('keanggotaan_ids', 'ketua_organisasi_ids')
    def _compute_sudah_berorganisasi(self):
        for record in self:
            record.sudah_berorganisasi = bool(
                record.keanggotaan_ids or record.ketua_organisasi_ids
            )

    def action_view_organisasi(self):
        self.ensure_one()
        organisasi_ids = self.keanggotaan_ids.mapped('organisasi_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Organisasi',
            'res_model': 'campus.organisasi',
            'view_mode': 'list,form',
            'domain': [('id', 'in', organisasi_ids)],
        }
