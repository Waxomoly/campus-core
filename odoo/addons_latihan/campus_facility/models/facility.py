from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CampusFacility(models.Model):
    _name = 'campus.facility'
    _description = 'Data Fasilitas / Ruangan'
    _order = 'name'

    kode = fields.Char(string='Kode Fasilitas', required=True, copy=False, index=True)
    name = fields.Char(string='Nama Fasilitas', required=True)
    tipe = fields.Selection([
        ('ruangan', 'Ruang Kelas'),
        ('lab', 'Laboratorium'),
        ('aula', 'Aula'),
        ('lain', 'Lainnya'),
    ], string='Tipe', default='ruangan', required=True)
    kapasitas = fields.Integer(string='Kapasitas', default=30, required=True)
    state = fields.Selection([
        ('tersedia', 'Tersedia'),
        ('maintenance', 'Maintenance'),
    ], string='Kondisi', default='tersedia', required=True, readonly=True, copy=False)
    booking_ids = fields.One2many(
        'campus.facility.booking', 'facility_id', string='Daftar Booking',
    )
    booking_count = fields.Integer(
        string='Jumlah Booking', compute='_compute_booking_count',
    )

    _kode_unique = models.Constraint('unique(kode)', 'Kode fasilitas sudah ada!')
    _kapasitas_positive = models.Constraint('CHECK(kapasitas > 0)', 'Kapasitas harus lebih dari 0!')

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for record in self:
            record.booking_count = len(record.booking_ids)

    @api.constrains('kapasitas')
    def _check_kapasitas(self):
        for record in self:
            if record.kapasitas <= 0:
                raise ValidationError("Kapasitas harus lebih besar dari 0!")

    # Workflow maintenance request
    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_set_available(self):
        self.write({'state': 'tersedia'})

    def action_view_booking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Booking',
            'res_model': 'campus.facility.booking',
            'view_mode': 'list,form',
            'domain': [('facility_id', '=', self.id)],
            'context': {'default_facility_id': self.id},
        }
