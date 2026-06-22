from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CampusRoomBooking(models.Model):
    _name = 'campus.room.booking'
    _description = 'Booking / Reservasi Ruangan'
    _order = 'tanggal_mulai desc'

    name = fields.Char(
        string='Nomor Booking', required=True, index=True,
        readonly=True, default='Draft', copy=False
    )
    room_id = fields.Many2one(
        'campus.room', string='Ruangan', required=True, ondelete='restrict',
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

    tipe_peminjam = fields.Selection([
        ('mahasiswa', 'Mahasiswa'),
        ('dosen', 'Dosen')
    ], string='Tipe Peminjam', required=True, default=lambda self: self._default_tipe_peminjam())

    # 2. Hapus required=True dari mahasiswa_id karena sekarang bisa jadi kosong jika yang pinjam Dosen
    mahasiswa_id = fields.Many2one(
        'campus.mahasiswa', string='Mahasiswa Peminjam', ondelete='restrict',
        default=lambda self: self._default_mahasiswa()
    )

    # 3. Tambahkan dosen_id
    dosen_id = fields.Many2one(
        'campus.dosen', string='Dosen Peminjam', ondelete='restrict',
        default=lambda self: self._default_dosen()
    )

    created_by_id = fields.Many2one('res.users', string='Dibuat Oleh', readonly=True,
                                    default=lambda self: self.env.user)
    status_changed_by_id = fields.Many2one('res.users', string='Status Diubah Oleh', readonly=True)

    peminjam_nama = fields.Char(string='Peminjam', compute='_compute_peminjam_nama')

    # TAMBAHKAN INI:
    is_facility_manager = fields.Boolean(compute='_compute_is_facility_manager')


    def _compute_is_facility_manager(self):
        for record in self:
            record.is_facility_manager = self.env.user.has_group('campus_facility.group_facility_manager')


    # ------------------------------------------------------------------
    # Override Create Method (Membuat nomor booking saat disimpan)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):

        is_manager = self.env.user.has_group('campus_facility.group_facility_manager')

        for vals in vals_list:

            tipe = vals.get('tipe_peminjam')

            if tipe == 'mahasiswa':
                vals['dosen_id'] = False
                mahasiswa_id = vals.get('mahasiswa_id') or self._default_mahasiswa()
                dosen_id = False
            elif tipe == 'dosen':
                vals['mahasiswa_id'] = False
                dosen_id = vals.get('dosen_id') or self._default_dosen()
                mahasiswa_id = False
            else:
                mahasiswa_id = vals.get('mahasiswa_id')
                dosen_id = vals.get('dosen_id')

            if not mahasiswa_id and not dosen_id and not is_manager:
                raise ValidationError(
                    "Anda tidak terdaftar sebagai dosen maupun mahasiswa di sistem. Kolom peminjam tidak dapat diisi. Mohon hubungi Admin."
                )

                # --- LOGIKA PENOMORAN SEQUENCE (Diadaptasi dari Facility Booking) ---
            if vals.get('name', 'Draft') == 'Draft' and vals.get('room_id'):
                room = self.env['campus.room'].browse(vals['room_id'])

                # Gunakan KODE ruangan untuk kode sequence agar unik
                seq_code = f"campus.room.booking.{room.kode}"

                # Cari apakah sequence untuk ruangan ini sudah pernah dibuat sebelumnya?
                sequence_obj = self.env['ir.sequence'].sudo().search([('code', '=', seq_code)], limit=1)

                if not sequence_obj:
                    # Jika belum ada, buat sequence on-the-fly
                    sequence_obj = self.env['ir.sequence'].sudo().create({
                        'name': f'Sequence Booking Ruangan - {room.name}',
                        'code': seq_code,
                        'prefix': f'BKR/{room.kode}/',  # Saya bedakan prefix-nya menjadi BKR (Booking Ruangan)
                        'padding': 5,
                        'number_next': 1,
                        'number_increment': 1,
                        'company_id': False,
                    })

                # Ambil nomor urut berikutnya
                vals['name'] = sequence_obj.next_by_id()

                # Set pengubah status pertama kali
            vals['status_changed_by_id'] = self.env.user.id

            return super(CampusRoomBooking, self).create(vals_list)

    # ------------------------------------------------------------------
    # Akses & Default Logged-In User
    # ------------------------------------------------------------------
    @api.model
    def _default_tipe_peminjam(self):
        dosen = self.env['campus.dosen'].search([('name', '=', self.env.user.name)], limit=1)
        return 'dosen' if dosen else 'mahasiswa'

    @api.model
    def _default_mahasiswa(self):
        mahasiswa = self.env['campus.mahasiswa'].search([('name', '=', self.env.user.name)], limit=1)
        return mahasiswa.id if mahasiswa else False

    @api.model
    def _default_dosen(self):
        dosen = self.env['campus.dosen'].search([('name', '=', self.env.user.name)], limit=1)
        return dosen.id if dosen else False

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
    # Depends
    # ------------------------------------------------------------------
    @api.depends('tipe_peminjam', 'mahasiswa_id', 'dosen_id')
    def _compute_peminjam_nama(self):
        for record in self:
            if record.tipe_peminjam == 'mahasiswa' and record.mahasiswa_id:
                record.peminjam_nama = record.mahasiswa_id.name
            elif record.tipe_peminjam == 'dosen' and record.dosen_id:
                record.peminjam_nama = record.dosen_id.name
            else:
                record.peminjam_nama = "-"

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
            record._check_room_availability()

    # ------------------------------------------------------------------
    # Helper Method: Pengecekan Ketersediaan Ruangan (Bentrokan/Overlap)
    # ------------------------------------------------------------------
    def _check_room_availability(self):
        """Memeriksa bentrokan jadwal booking untuk ruangan yang sama."""
        for record in self:
            if record.room_id and record.tanggal_mulai and record.tanggal_selesai:
                overlap = self.search([
                    ('id', '!=', record.id),
                    ('room_id', '=', record.room_id.id),
                    ('state', 'in', ('submitted', 'approved')),
                    ('tanggal_mulai', '<', record.tanggal_selesai),
                    ('tanggal_selesai', '>', record.tanggal_mulai),
                ], limit=1)

                if overlap:
                    raise ValidationError(
                        f"Gagal memproses! Ruangan '{record.room_id.name}' sudah dibooking "
                        f"pada rentang waktu tersebut oleh nomor booking: {overlap.name}."
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
            record._check_room_availability()
            record.state = 'submitted'

    def action_approve(self):
        for record in self:
            record._check_room_availability()

        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset(self):
        self.write({'state': 'draft'})

