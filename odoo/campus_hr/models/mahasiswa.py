from odoo import models, fields, api


class CampusMahasiswa(models.Model):
    _inherit = 'campus.mahasiswa'

    keanggotaan_ids = fields.One2many(
        'campus.organisasi.anggota', 'mahasiswa_id', string='Keanggotaan Organisasi',
    )
    organisasi_count = fields.Integer(
        string='Jumlah Organisasi', compute='_compute_organisasi_count',
    )

    @api.depends('keanggotaan_ids')
    def _compute_organisasi_count(self):
        for record in self:
            record.organisasi_count = len(record.keanggotaan_ids.mapped('organisasi_id'))

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
