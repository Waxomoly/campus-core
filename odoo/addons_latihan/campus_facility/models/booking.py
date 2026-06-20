from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CampusFacilityBooking(models.Model):
    _name = 'campus.facility.booking'
    _description = 'Booking / Reservasi Fasilitas'
    _order = 'tanggal_mulai desc'

    name = fields.Char(
        string='Nomor Booking', compute='_compute_name', store=True,
        readonly=True, default='Draft',
    )
    facility_id = fields.Many2one(
        'campus.facility', string='Fasilitas', required=True, ondelete='restrict',
    )
    mahasiswa_id = fields.Many2one(
        'campus.mahasiswa', string='Peminjam', required=True, ondelete='restrict',
    )
    keperluan = fields.Char(string='Keperluan', required=True)
    tanggal_mulai = fields.Datetime(string='Mulai', required=True)
    tanggal_selesai = fields.Datetime(string='Selesai', required=True)
    jumlah_peserta = fields.Integer(string='Jumlah Peserta', default=1)
    kapasitas = fields.Integer(
        string='Kapasitas Ruang', related='facility_id.kapasitas', readonly=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('facility_id.kode', 'mahasiswa_id.nim')
    def _compute_name(self):
        for record in self:
            if record.facility_id and record.mahasiswa_id:
                record.name = "BK/%s/%s" % (
                    record.facility_id.kode, record.mahasiswa_id.nim,
                )
            else:
                record.name = 'Draft'

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('facility_id', 'jumlah_peserta')
    def _onchange_facility(self):
        if self.facility_id and self.jumlah_peserta > self.facility_id.kapasitas:
            return {
                'warning': {
                    'title': 'Kapasitas Terlampaui',
                    'message': 'Jumlah peserta (%s) melebihi kapasitas ruang (%s).' % (
                        self.jumlah_peserta, self.facility_id.kapasitas,
                    ),
                }
            }

    # ------------------------------------------------------------------
    # Constraint
    # ------------------------------------------------------------------
    @api.constrains('tanggal_mulai', 'tanggal_selesai', 'jumlah_peserta')
    def _check_booking(self):
        for record in self:
            if record.tanggal_selesai <= record.tanggal_mulai:
                raise ValidationError("Tanggal selesai harus setelah tanggal mulai!")
            if record.jumlah_peserta > record.facility_id.kapasitas:
                raise ValidationError(
                    "Jumlah peserta melebihi kapasitas fasilitas (%s)!"
                    % record.facility_id.kapasitas
                )
            # cek bentrok dengan booking lain yang aktif
            overlap = self.search([
                ('id', '!=', record.id),
                ('facility_id', '=', record.facility_id.id),
                ('state', 'in', ('submitted', 'approved')),
                ('tanggal_mulai', '<', record.tanggal_selesai),
                ('tanggal_selesai', '>', record.tanggal_mulai),
            ], limit=1)
            if overlap:
                raise ValidationError(
                    "Fasilitas sudah dibooking pada rentang waktu tersebut (%s)!"
                    % overlap.name
                )

    # ------------------------------------------------------------------
    # Override method (unlink) -> super()
    # ------------------------------------------------------------------
    def unlink(self):
        for record in self:
            if record.state == 'approved':
                raise ValidationError("Booking yang sudah Approved tidak bisa dihapus!")
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        for record in self:
            if record.facility_id.state == 'maintenance':
                raise ValidationError(
                    "Fasilitas sedang Maintenance, tidak bisa dibooking!"
                )
            record.state = 'submitted'

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset(self):
        self.write({'state': 'draft'})
