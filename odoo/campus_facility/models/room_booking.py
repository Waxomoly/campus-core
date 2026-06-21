from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CampusRoomBooking(models.Model):
    _name = 'campus.room.booking'
    _description = 'Booking / Reservasi Ruangan'
    _order = 'tanggal_mulai desc'

    name = fields.Char(
        string='Nomor Booking', compute='_compute_name', store=True,
        readonly=True, default='Draft',
    )
    room_id = fields.Many2one(
        'campus.room', string='Ruangan', required=True, ondelete='restrict',
    )
    mahasiswa_id = fields.Many2one(
        'campus.mahasiswa', string='Peminjam', required=True, ondelete='restrict',
    )
    keperluan = fields.Char(string='Keperluan', required=True)
    tanggal_mulai = fields.Datetime(string='Mulai', required=True)
    tanggal_selesai = fields.Datetime(string='Selesai', required=True)
    jumlah_peserta = fields.Integer(string='Jumlah Peserta', default=1)
    kapasitas = fields.Integer(
        string='Kapasitas Ruang', related='room_id.kapasitas', readonly=True,
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
    @api.depends('room_id.kode', 'mahasiswa_id.nim')
    def _compute_name(self):
        for record in self:
            if record.room_id and record.mahasiswa_id:
                record.name = "BK/%s/%s" % (
                    record.room_id.kode, record.mahasiswa_id.nim,
                )
            else:
                record.name = 'Draft'

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('room_id', 'jumlah_peserta')
    def _onchange_room(self):
        if self.room_id and self.jumlah_peserta > self.room_id.kapasitas:
            return {
                'warning': {
                    'title': 'Kapasitas Terlampaui',
                    'message': 'Jumlah peserta (%s) melebihi kapasitas ruang (%s).' % (
                        self.jumlah_peserta, self.room_id.kapasitas,
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
            if record.jumlah_peserta > record.room_id.kapasitas:
                raise ValidationError(
                    "Jumlah peserta melebihi kapasitas ruangan (%s)!"
                    % record.room_id.kapasitas
                )
            # cek bentrok dengan booking lain yang aktif
            overlap = self.search([
                ('id', '!=', record.id),
                ('room_id', '=', record.room_id.id),
                ('state', 'in', ('submitted', 'approved')),
                ('tanggal_mulai', '<', record.tanggal_selesai),
                ('tanggal_selesai', '>', record.tanggal_mulai),
            ], limit=1)
            if overlap:
                raise ValidationError(
                    "Ruangan sudah dibooking pada rentang waktu tersebut (%s)!"
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
            if record.room_id.state == 'maintenance':
                raise ValidationError(
                    "Ruangan sedang Maintenance, tidak bisa dibooking!"
                )
            record.state = 'submitted'

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset(self):
        self.write({'state': 'draft'})
