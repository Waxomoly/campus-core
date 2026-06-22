from odoo import models, fields, api


class CampusMahasiswa(models.Model):
    _inherit = 'campus.mahasiswa'

    booking_ids = fields.One2many(
        'campus.facility.booking', 'mahasiswa_id', string='Booking Fasilitas',
    )
    booking_count = fields.Integer(
        string='Jumlah Booking', compute='_compute_booking_count',
    )

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for record in self:
            record.booking_count = len(record.booking_ids)

    def action_view_booking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Booking Fasilitas',
            'res_model': 'campus.facility.booking',
            'view_mode': 'list,form',
            'domain': [('mahasiswa_id', '=', self.id)],
            'context': {'default_mahasiswa_id': self.id},
        }
