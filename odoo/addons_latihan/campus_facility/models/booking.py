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

    kuantitas_pinjam = fields.Integer(string='Jumlah Dipinjam', default=1, required=True)

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
    # Constraint
    # ------------------------------------------------------------------
    @api.constrains('tanggal_mulai', 'tanggal_selesai', 'kuantitas_pinjam', 'facility_id')
    def _check_booking(self):
        for record in self:

            if record.kuantitas_pinjam <= 0:
                raise ValidationError("Jumlah dipinjam harus lebih dari 0!")

            # Cari booking LAIN di fasilitas yang sama dan waktunya bertabrakan/overlap
            overlapping_bookings = self.env['campus.facility.booking'].search([
                ('id', '!=', record.id),
                ('facility_id', '=', record.facility_id.id),
                ('state', 'in', ['submitted', 'approved']),
                ('tanggal_mulai', '<', record.tanggal_selesai),
                ('tanggal_selesai', '>', record.tanggal_mulai),
            ])

            # Hitung total kuantitas yang sudah dibooking pada jam tersebut
            total_dipinjam = sum(overlapping_bookings.mapped('kuantitas_pinjam'))

            # Asumsi field kuantitas di model facility Anda bernama 'kuantitas'
            kuantitas_maksimal = record.facility_id.kuantitas

            # Jika total pinjaman melebihi batas, tolak!
            if (total_dipinjam + record.kuantitas_pinjam) > kuantitas_maksimal:
                sisa = kuantitas_maksimal - total_dipinjam
                raise ValidationError(
                    f"Kuantitas tidak mencukupi!\n"
                    f"Fasilitas '{record.facility_id.name}' pada jadwal tersebut sudah dipinjam {total_dipinjam} unit.\n"
                    f"Sisa yang bisa dipinjam pada waktu tersebut: {sisa} unit."
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
