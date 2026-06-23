from odoo import models, fields, api
from odoo.exceptions import ValidationError

# Batas maksimum SKS yang boleh diambil dalam satu KRS
MAX_SKS = 24


class CampusKRS(models.Model):
    _name = 'campus.krs'
    _description = 'KRS / Enrollment Mahasiswa'
    _order = 'create_date desc'

    name = fields.Char(
        string='Nomor KRS', compute='_compute_name',
        store=True, readonly=True, default='Draft KRS',
    )
    mahasiswa_id = fields.Many2one(
        'campus.mahasiswa', string='Mahasiswa',
        required=True, ondelete='restrict',
    )
    dosen_pembimbing_id = fields.Many2one(
        'campus.dosen', string='Dosen Pembimbing Akademik', ondelete='restrict',
    )
    semester = fields.Char(
        string='Semester', required=True,
        default=lambda self: self._default_semester(),
        help='Contoh: Genap 2025/2026',
    )
    line_ids = fields.One2many(
        'campus.krs.line', 'krs_id', string='Mata Kuliah Diambil',
    )
    total_sks = fields.Integer(
        string='Total SKS', compute='_compute_total_sks', store=True,
    )
    # Daftar kelas yang boleh diambil mahasiswa ini (filter cakupan + kuota)
    allowed_kelas_ids = fields.Many2many(
        'campus.kelas', string='Kelas Tersedia',
        compute='_compute_allowed_kelas',
    )
    # Status makro KRS (keseluruhan lembar)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('processed', 'Processed'),
    ], string='Status KRS', default='draft', required=True,
        readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Default
    # ------------------------------------------------------------------
    @api.model
    def _default_semester(self):
        """Semester berjalan, ter-generate otomatis dari tanggal hari ini.

        Format konsisten dengan Semester Aktif Mahasiswa & Kelas,
        mis. 'Genap 2025/2026'.
        """
        today = fields.Date.context_today(self)
        if today.month >= 8:
            return "Gasal %d/%d" % (today.year, today.year + 1)
        if today.month == 1:
            return "Gasal %d/%d" % (today.year - 1, today.year)
        return "Genap %d/%d" % (today.year - 1, today.year)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('line_ids.sks')
    def _compute_total_sks(self):
        for record in self:
            record.total_sks = sum(record.line_ids.mapped('sks'))

    @api.depends('mahasiswa_id', 'semester')
    def _compute_allowed_kelas(self):
        Kelas = self.env['campus.kelas']
        for record in self:
            if not record.mahasiswa_id or not record.semester:
                record.allowed_kelas_ids = Kelas
                continue
            kelas = Kelas.search([
                ('semester', '=', record.semester),
                ('is_available', '=', True),
            ])
            record.allowed_kelas_ids = kelas.filtered(
                lambda k: self._is_kelas_eligible(k, record.mahasiswa_id)
            )

    @staticmethod
    def _is_kelas_eligible(kelas, mahasiswa):
        # Semua kelas/mata kuliah terbuka untuk semua mahasiswa,
        # tanpa memandang Fakultas/Prodi/Jurusan.
        return True

    @api.depends('mahasiswa_id.nim', 'semester')
    def _compute_name(self):
        for record in self:
            if record.mahasiswa_id and record.semester:
                record.name = "KRS/%s/%s" % (
                    record.mahasiswa_id.nim,
                    record.semester.replace(' ', '_'),
                )
            else:
                record.name = 'Draft KRS'

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('total_sks')
    def _check_total_sks(self):
        for record in self:
            if record.total_sks > MAX_SKS:
                raise ValidationError(
                    "Total SKS (%s) melebihi batas maksimum %s SKS!"
                    % (record.total_sks, MAX_SKS)
                )

    @api.constrains('mahasiswa_id')
    def _check_mahasiswa_aktif(self):
        """Hanya mahasiswa berstatus Aktif yang boleh mengisi KRS."""
        status_labels = dict(
            self.env['campus.mahasiswa']._fields['status'].selection
        )
        for record in self:
            mhs = record.mahasiswa_id
            if mhs and mhs.status != 'aktif':
                raise ValidationError(
                    "Mahasiswa %s berstatus '%s'. Hanya mahasiswa berstatus "
                    "Aktif yang boleh mengisi KRS."
                    % (mhs.name, status_labels.get(mhs.status, mhs.status))
                )

    @api.onchange('mahasiswa_id')
    def _onchange_mahasiswa_aktif(self):
        if self.mahasiswa_id and self.mahasiswa_id.status != 'aktif':
            return {
                'warning': {
                    'title': 'Mahasiswa Tidak Aktif',
                    'message': "Mahasiswa ini tidak berstatus Aktif, "
                               "sehingga tidak dapat mengisi KRS.",
                }
            }

    @api.constrains('line_ids')
    def _check_unique_mata_kuliah(self):
        """Mahasiswa hanya boleh mengambil 1 kelas per mata kuliah."""
        for record in self:
            mk = record.line_ids.mapped('mata_kuliah_id')
            if len(mk) != len(record.line_ids):
                raise ValidationError(
                    "Setiap mata kuliah hanya boleh diambil 1 kelas "
                    "dalam satu KRS!"
                )

    # ------------------------------------------------------------------
    # Validasi bisnis sebelum kunci KRS
    # ------------------------------------------------------------------
    def _validate_jadwal_bentrok(self):
        """Cegah pengambilan kelas dengan jadwal bentrok."""
        self.ensure_one()
        kelas_list = self.line_ids.mapped('kelas_id')
        for i, kelas in enumerate(kelas_list):
            for other in kelas_list[i + 1:]:
                if kelas.is_bentrok_with(other):
                    raise ValidationError(
                        "Jadwal bentrok antara '%s' dan '%s'. "
                        "Silakan pilih kelas lain."
                        % (kelas.display_name, other.display_name)
                    )

    def _validate_kuota(self):
        """Pastikan setiap kelas masih punya kuota (sistem rebutan/FCFS)."""
        self.ensure_one()
        for line in self.line_ids:
            kelas = line.kelas_id
            # Hitung peserta yang sudah mengunci kuota, KECUALI baris ini sendiri
            terpakai = self.env['campus.krs.line'].search_count([
                ('kelas_id', '=', kelas.id),
                ('krs_id', '!=', self.id),
                ('krs_state', 'in', ('submitted', 'processed')),
                ('state', '!=', 'rejected'),
            ])
            if terpakai >= kelas.kuota:
                raise ValidationError(
                    "Kelas '%s' sudah penuh (kuota %s). "
                    "Silakan pilih kelas lain yang masih tersedia."
                    % (kelas.display_name, kelas.kuota)
                )

    def _validate_eligibility(self):
        """Pastikan setiap kelas sesuai cakupan (Fakultas/Prodi/Jurusan) mahasiswa."""
        self.ensure_one()
        for line in self.line_ids:
            if not self._is_kelas_eligible(line.kelas_id, self.mahasiswa_id):
                raise ValidationError(
                    "Mata kuliah '%s' tidak tersedia untuk mahasiswa ini "
                    "(tidak sesuai cakupan Fakultas/Prodi/Jurusan)."
                    % (line.kelas_id.mata_kuliah_id.name or line.kelas_id.display_name,)
                )

    # ------------------------------------------------------------------
    # Workflow  (Student & Lecturer)
    # ------------------------------------------------------------------
    def action_submit(self):
        """Mahasiswa mengunci KRS -> state submitted."""
        for record in self:
            if record.state != 'draft':
                raise ValidationError("KRS hanya bisa di-submit dari status Draft!")
            if not record.line_ids:
                raise ValidationError(
                    "Anda harus memilih minimal satu Mata Kuliah "
                    "sebelum submit KRS!"
                )
            record._validate_eligibility()
            record._validate_jadwal_bentrok()
            record._validate_kuota()
            record.state = 'submitted'

    def action_process(self):
        """Dosen menyelesaikan pemeriksaan -> state processed."""
        for record in self:
            if record.state != 'submitted':
                raise ValidationError(
                    "KRS hanya bisa diproses dari status Submitted!"
                )
            pending = record.line_ids.filtered(lambda l: l.state == 'pending')
            if pending:
                raise ValidationError(
                    "Masih ada %s mata kuliah berstatus Pending. "
                    "Dosen harus menyetujui/menolak semua mata kuliah "
                    "sebelum KRS diproses." % len(pending)
                )
            record.state = 'processed'

    def action_reset(self):
        """Kembali ke draft (selama belum diproses)."""
        for record in self:
            if record.state == 'processed':
                raise ValidationError(
                    "KRS yang sudah Processed tidak bisa dikembalikan ke Draft!"
                )
            record.line_ids.write({'state': 'pending'})
            record.state = 'draft'


class CampusKRSLine(models.Model):
    _name = 'campus.krs.line'
    _description = 'Baris Mata Kuliah pada KRS'
    _order = 'krs_id, mata_kuliah_id'

    krs_id = fields.Many2one(
        'campus.krs', string='KRS', required=True,
        ondelete='cascade', index=True,
    )
    kelas_id = fields.Many2one(
        'campus.kelas', string='Kelas', required=True, ondelete='restrict',
    )
    mata_kuliah_id = fields.Many2one(
        'campus.mata_kuliah', string='Mata Kuliah',
        related='kelas_id.mata_kuliah_id', store=True, readonly=True,
    )
    sks = fields.Integer(
        string='SKS', related='kelas_id.sks', store=True, readonly=True,
    )
    dosen_id = fields.Many2one(
        related='kelas_id.dosen_id', string='Dosen', store=True, readonly=True,
    )
    hari = fields.Selection(
        related='kelas_id.hari', string='Hari', store=True, readonly=True,
    )
    jam_mulai = fields.Float(related='kelas_id.jam_mulai', string='Jam Mulai', readonly=True)
    jam_selesai = fields.Float(related='kelas_id.jam_selesai', string='Jam Selesai', readonly=True)
    ruangan = fields.Char(related='kelas_id.ruangan', string='Ruangan', readonly=True)

    # Status per-record (diatur oleh dosen)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending', required=True, copy=False)

    # Status KRS induk (untuk perhitungan kuota kelas)
    krs_state = fields.Selection(
        related='krs_id.state', string='Status KRS',
        store=True, readonly=True,
    )

    # ------------------------------------------------------------------
    # Aksi dosen per baris mata kuliah
    # ------------------------------------------------------------------
    def action_approve_line(self):
        self.write({'state': 'approved'})

    def action_reject_line(self):
        self.write({'state': 'rejected'})

    def action_reset_line(self):
        self.write({'state': 'pending'})
