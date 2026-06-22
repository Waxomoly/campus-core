from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError



class CampusFacilityBooking(models.Model):
    _name = 'campus.facility.booking'
    _description = 'Booking / Reservasi Fasilitas'
    _order = 'tanggal_mulai desc'

    name = fields.Char(
        string='Nomor Booking', required=True, index=True,
        readonly=True, default='Draft', copy=False
    )
    facility_id = fields.Many2one(
        'campus.facility', string='Fasilitas', required=True, ondelete='restrict',
    )


    is_facility_manager = fields.Boolean(compute='_compute_is_facility_manager')

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
    keperluan = fields.Char(string='Keperluan', required=True)
    tanggal_mulai = fields.Datetime(string='Mulai', required=True)
    tanggal_selesai = fields.Datetime(string='Selesai', required=True)

    kuantitas_pinjam = fields.Integer(string='Jumlah Dipinjam', default=1, required=True)

    kuantitas_tersedia = fields.Integer(
        string='Sisa Tersedia', compute='_compute_kuantitas_tersedia'
    )

    created_by_id = fields.Many2one('res.users', string='Dibuat Oleh', readonly=True,
                                    default=lambda self: self.env.user)
    status_changed_by_id = fields.Many2one('res.users', string='Status Diubah Oleh', readonly=True)

    peminjam_nama = fields.Char(string='Peminjam', compute='_compute_peminjam_nama')


    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, readonly=True, copy=False)

    @api.depends('tipe_peminjam', 'mahasiswa_id', 'dosen_id')
    def _compute_peminjam_nama(self):
        for record in self:
            if record.tipe_peminjam == 'mahasiswa' and record.mahasiswa_id:
                record.peminjam_nama = record.mahasiswa_id.name
            elif record.tipe_peminjam == 'dosen' and record.dosen_id:
                record.peminjam_nama = record.dosen_id.name
            else:
                record.peminjam_nama = "-"

    @api.depends('facility_id', 'tanggal_mulai', 'tanggal_selesai')
    def _compute_kuantitas_tersedia(self):
        for record in self:
            if (not record.facility_id) or (not record.tanggal_mulai or not record.tanggal_selesai):
                # Jika fasilitas kosong, default ke 0
                record.kuantitas_tersedia = 0
            else:
                # Jika semua terisi, hitung yang bertabrakan (overlap)
                domain = [
                    ('facility_id', '=', record.facility_id.id),
                    ('state', 'in', ['submitted', 'approved']),
                    ('tanggal_mulai', '<', record.tanggal_selesai),
                    ('tanggal_selesai', '>', record.tanggal_mulai),
                ]

                # Hindari menghitung diri sendiri saat sedang di-edit
                if record._origin.id:
                    domain.append(('id', '!=', record._origin.id))

                overlapping_bookings = self.env['campus.facility.booking'].search(domain)
                total_dipinjam = sum(overlapping_bookings.mapped('kuantitas_pinjam'))

                # Kapasitas total dikurangi yang sedang dipinjam orang lain
                record.kuantitas_tersedia = record.facility_id.kuantitas - total_dipinjam

    # 3. Fungsi Onchange untuk Validasi Tanggal
    @api.onchange('tanggal_mulai', 'tanggal_selesai')
    def _onchange_tanggal_validasi(self):
        if self.tanggal_mulai and self.tanggal_selesai:
            if self.tanggal_mulai >= self.tanggal_selesai:
                # Jika tidak masuk akal, reset input selesai dan lempar warning
                # self.tanggal_selesai = False
                return {
                    'warning': {
                        'title': 'Jadwal Tidak Valid',
                        'message': 'Waktu Selesai harus lebih besar (setelah) Waktu Mulai.'
                    }
                }


    @api.model_create_multi
    def create(self, vals_list):

        is_manager = self.env.user.has_group('campus_facility.group_facility_manager')

        for vals in vals_list:

            tipe = vals.get('tipe_peminjam')

            if tipe == 'mahasiswa':
                # Jika tipe mahasiswa, pastikan dosen_id dipaksa KOSONG (None/False)
                vals['dosen_id'] = False
                mahasiswa_id = vals.get('mahasiswa_id') or self._default_mahasiswa()
                dosen_id = False
            elif tipe == 'dosen':
                # Jika tipe dosen, pastikan mahasiswa_id dipaksa KOSONG (None/False)
                vals['mahasiswa_id'] = False
                dosen_id = vals.get('dosen_id') or self._default_dosen()
                mahasiswa_id = False
            else:
                # Jika manager yang input tanpa memilih tipe, ambil data apa adanya
                mahasiswa_id = vals.get('mahasiswa_id')
                dosen_id = vals.get('dosen_id')

            # Gunakan variabel hasil pengecekan di atas untuk validasi
            if not mahasiswa_id and not dosen_id and not is_manager:
                raise ValidationError(
                    "Anda tidak terdaftar sebagai dosen maupun mahasiswa di sistem. Kolom peminjam tidak dapat diisi. Mohon hubungi Admin."
                )

            if vals.get('name', 'Draft') == 'Draft' and vals.get('facility_id'):
                facility = self.env['campus.facility'].browse(vals['facility_id'])

                # Gunakan KODE fasilitas (misal: LAB) untuk kode sequence agar unik dan rapi
                seq_code = f"campus.facility.booking.{facility.kode}"

                # Cari apakah sequence untuk kode fasilitas ini sudah pernah dibuat sebelumnya?
                sequence_obj = self.env['ir.sequence'].sudo().search([('code', '=', seq_code)], limit=1)

                if not sequence_obj:
                    # Jika belum ada, buat baru secara otomatis (on-the-fly)
                    sequence_obj = self.env['ir.sequence'].sudo().create({
                        'name': f'Sequence Booking Fasilitas - {facility.name}',
                        'code': seq_code,
                        'prefix': f'BK/{facility.kode}/',
                        'padding': 5,
                        'number_next': 1,
                        'number_increment': 1,
                        'company_id': False,
                    })

                # Ambil nomor urut berikutnya (Aman dari loncat/boros nomor)
                vals['name'] = sequence_obj.next_by_id()

            # Set pengubah status pertama kali adalah pembuatnya sendiri saat draft
            vals['status_changed_by_id'] = self.env.user.id
        return super(CampusFacilityBooking, self).create(vals_list)

    def write(self, vals):
        # Jika ada perubahan status ('state')
        if 'state' in vals:
            for record in self:
                # ATURAN: Hanya boleh diset ke draft jika user yang sedang login adalah pembuatnya
                if vals['state'] == 'draft' and record.created_by_id != self.env.user:
                    raise UserError(
                        "Hanya pengguna yang membuat reservasi ini (%s) yang dapat mengembalikannya ke status Draft!" % record.created_by_id.name)

                # Catat siapa yang mengubah status terakhir kali
                vals['status_changed_by_id'] = self.env.user.id

        return super(CampusFacilityBooking, self).write(vals)


    # ------------------------------------------------------------------
    # Akses & Default Logged-In User
    # ------------------------------------------------------------------
    def _compute_is_facility_manager(self):
        for record in self:
            record.is_facility_manager = self.env.user.has_group('campus_facility.group_facility_manager')

    @api.model
    def _default_tipe_peminjam(self):
        # Cek apakah nama user login ada di tabel Dosen
        # dosen = self.env['campus.dosen'].search([('name', '=', self.env.user.name)], limit=1)
        # return 'dosen' if dosen else 'mahasiswa'
        if self.env.user.has_group('campus_core.group_campus_lecturer'):
            return 'dosen'
        # elif self.env.user.has_group('campus_core.group_campus_mahasiswa'):
        #     return 'mahasiswa'
        else:
            return 'mahasiswa'

    @api.model
    def _default_mahasiswa(self):
        if self.env.user.has_group('campus_core.group_campus_student'):
            # Ganti 'name' menjadi 'user_id' jika Master Mahasiswa Anda sudah punya relasi akun Odoo
            mahasiswa = self.env['campus.mahasiswa'].search([('name', '=', self.env.user.name)], limit=1)
            return mahasiswa.id if mahasiswa else False
        return False

    @api.model
    def _default_dosen(self):
        if self.env.user.has_group('campus_core.group_campus_lecturer'):
            # Ganti 'name' menjadi 'user_id' jika Master Dosen Anda sudah punya relasi akun Odoo
            dosen = self.env['campus.dosen'].search([('name', '=', self.env.user.name)], limit=1)
            return dosen.id if dosen else False
        return False

    # ------------------------------------------------------------------
    # Constraint
    # ------------------------------------------------------------------
    @api.constrains('tanggal_mulai', 'tanggal_selesai', 'kuantitas_pinjam', 'facility_id')
    def _check_booking(self):
        for record in self:

            if record.tanggal_mulai and record.tanggal_selesai:
                if record.tanggal_mulai >= record.tanggal_selesai:
                    raise ValidationError(
                        f"Waktu Selesai harus lebih besar dari Waktu Mulai!"
                    )

            if record.kuantitas_pinjam <= 0:
                raise ValidationError("Jumlah dipinjam harus lebih dari 0!")

            record._check_facility_availability()

    # ------------------------------------------------------------------
    # Override method (unlink) -> super()
    # ------------------------------------------------------------------
    def unlink(self):
        # Cek apakah user yang sedang login adalah Manager
        is_manager = self.env.user.has_group('campus_facility.group_facility_manager')

        for record in self:
            # Aturan 1: Booking yang sudah Approved tidak boleh dihapus oleh SIAPA PUN (Manager maupun Non-Manager)
            if record.state == 'approved':
                raise ValidationError("Booking yang sudah Approved tidak bisa dihapus!")

            # Aturan 2: Proteksi khusus untuk NON-MANAGER
            if not is_manager:
                # Non-manager HANYA boleh menghapus jika statusnya masih 'draft'
                if record.state != 'draft':
                    raise ValidationError(
                        "Anda hanya boleh menghapus reservasi yang masih berstatus Draft.")

                # AMBIL DATA PEMINJAM YANG SEDANG LOGIN
                current_mahasiswa = self.env['campus.mahasiswa'].search([('name', '=', self.env.user.name)],
                                                                        limit=1)
                current_dosen = self.env['campus.dosen'].search([('name', '=', self.env.user.name)], limit=1)

                # VALIDASI BARU: Jika draf tersebut milik mahasiswa/dosen yang sedang login, TOLAK!
                if (record.tipe_peminjam == 'mahasiswa' and record.mahasiswa_id == current_mahasiswa) or \
                        (record.tipe_peminjam == 'dosen' and record.dosen_id == current_dosen):
                    raise ValidationError(
                        "Anda tidak diizinkan menghapus draf reservasi Anda sendiri! "
                        "Mohon hubungi Admin/Manager jika ingin membatalkannya."
                    )

        # Jika lolos semua pengecekan di atas, jalankan fungsi hapus bawaan Odoo
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

            record._check_facility_availability()

            record.state = 'submitted'

    def action_approve(self):
        for record in self:
            # Panggil fungsi pusat sebelum merubah status menjadi approved
            record._check_facility_availability()

        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def _check_facility_availability(self):
        """Fungsi mandiri untuk memeriksa ketersediaan kuantitas fasilitas."""
        for record in self:
            if record.facility_id and record.tanggal_mulai and record.tanggal_selesai:
                # Cari booking LAIN yang bertabrakan jadwal
                overlapping_bookings = self.env['campus.facility.booking'].search([
                    ('id', '!=', record.id),
                    ('facility_id', '=', record.facility_id.id),
                    ('state', 'in', ['submitted', 'approved']),
                    ('tanggal_mulai', '<', record.tanggal_selesai),
                    ('tanggal_selesai', '>', record.tanggal_mulai),
                ])

                # Hitung sisa stok
                total_dipinjam = sum(overlapping_bookings.mapped('kuantitas_pinjam'))
                kuantitas_maksimal = record.facility_id.kuantitas
                sisa_tersedia = kuantitas_maksimal - total_dipinjam

                # Lempar error jika kuantitas yang diminta tidak mencukupi
                if record.kuantitas_pinjam > sisa_tersedia:
                    raise ValidationError(
                        f"Kuantitas tidak mencukupi untuk jadwal ini!\n\n"
                        f"Fasilitas: '{record.facility_id.name}'\n"
                        f"Sisa Tersedia: {max(0, sisa_tersedia)} unit.\n"
                        f"Anda meminta: {record.kuantitas_pinjam} unit."
                    )
