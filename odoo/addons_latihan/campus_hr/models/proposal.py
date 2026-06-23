from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError


class CampusProposal(models.Model):
    _name = 'campus.proposal'
    _description = 'Proposal Kegiatan Organisasi'
    _order = 'create_date desc'

    name = fields.Char(
        string='Nomor Proposal', required=True, copy=False,
        readonly=True, default='New',
    )
    judul = fields.Char(string='Judul Kegiatan', required=True)
    organisasi_id = fields.Many2one(
        'campus.organisasi', string='Organisasi', required=True, ondelete='cascade',
    )
    pembina_id = fields.Many2one(
        'campus.dosen', string='Dosen Pembina',
        related='organisasi_id.pembina_id', store=True, readonly=True,
    )
    tipe_id = fields.Many2one(
        'campus.organisasi.tipe', string='Tipe Organisasi',
        related='organisasi_id.tipe_id', store=True, readonly=True,
    )
    ketua_panitia_id = fields.Many2one(
        'campus.mahasiswa', string='Ketua Panitia', ondelete='restrict',
        help='Default mengikuti Ketua Umum organisasi, namun boleh diganti.',
    )
    tanggal_kegiatan = fields.Date(string='Tanggal Kegiatan', required=True)
    anggaran = fields.Float(string='Anggaran (Rp)', default=0.0)
    deskripsi = fields.Text(string='Deskripsi Kegiatan (opsional)')
    # Dokumen proposal lengkap (Word/PDF/file apapun)
    file_proposal = fields.Binary(string='File Proposal', attachment=True)
    file_proposal_name = fields.Char(string='Nama File')
    panitia_ids = fields.One2many(
        'campus.proposal.panitia', 'proposal_id', string='Struktur Kepanitiaan',
    )

    # Nomor urut kegiatan dalam satu organisasi (dasar penomoran)
    no_kegiatan = fields.Integer(string='No. Kegiatan', readonly=True, copy=False)
    # Tanggal proposal diajukan (untuk bulan pada nomor)
    tanggal_masuk = fields.Date(string='Tanggal Diajukan', readonly=True, copy=False)
    # Tanggal proposal disetujui (untuk tahun pada nomor)
    tanggal_disetujui = fields.Date(string='Tanggal Disetujui', readonly=True, copy=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Helper penomoran
    # ------------------------------------------------------------------
    @staticmethod
    def _konsonan(text):
        """Ambil huruf konsonan saja (vokal & non-huruf dibuang), uppercase."""
        if not text:
            return ''
        vokal = set('AIUEO')
        return ''.join(ch for ch in text.upper() if ch.isalpha() and ch not in vokal)

    @staticmethod
    def _int_to_roman(num):
        angka = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
                 (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
                 (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
        hasil = ''
        for nilai, simbol in angka:
            while num >= nilai:
                hasil += simbol
                num -= nilai
        return hasil

    def _next_no_kegiatan(self):
        """Nomor urut kegiatan berikutnya untuk organisasi ini."""
        self.ensure_one()
        terakhir = self.search([
            ('organisasi_id', '=', self.organisasi_id.id),
            ('no_kegiatan', '>', 0),
        ], order='no_kegiatan desc', limit=1)
        return (terakhir.no_kegiatan or 0) + 1

    def _build_nomor(self, no_kegiatan, tanggal_masuk, tahun_disetujui):
        """Format:
        [No.Kegiatan]/[Konsonan Judul]/[Kode Organisasi]/PCU/[Bulan Romawi]/[Tahun]
        contoh: 001/NVSTLK/HIMA/PCU/VI/2026
        """
        self.ensure_one()
        return "%03d/%s/%s/PCU/%s/%s" % (
            no_kegiatan,
            self._konsonan(self.judul) or 'X',
            (self.organisasi_id.kode or '-').upper(),
            self._int_to_roman(tanggal_masuk.month),
            tahun_disetujui,
        )

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('organisasi_id')
    def _onchange_organisasi_id(self):
        # Default Ketua Panitia = Ketua Umum organisasi (tetap bisa diganti).
        if self.organisasi_id:
            self.ketua_panitia_id = self.organisasi_id.ketua_id

    # ------------------------------------------------------------------
    # Constraint
    # ------------------------------------------------------------------
    @api.constrains('anggaran')
    def _check_anggaran(self):
        for record in self:
            if record.anggaran < 0:
                raise ValidationError("Anggaran tidak boleh bernilai negatif!")

    # ------------------------------------------------------------------
    # Override method (create / write / unlink) -> super()
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('organisasi_id'):
                organisasi = self.env['campus.organisasi'].browse(vals['organisasi_id'])
                if organisasi.state == 'nonaktif':
                    raise ValidationError(
                        "Organisasi Non-Aktif tidak dapat membuat proposal baru!"
                    )
        return super().create(vals_list)

    def write(self, vals):
        for record in self:
            editing_other = set(vals) - {'state'}
            if record.state == 'approved' and editing_other:
                raise ValidationError(
                    "Proposal yang sudah Approved tidak bisa diubah!"
                )
        return super().write(vals)

    def unlink(self):
        for record in self:
            if record.state in ('submitted', 'approved'):
                raise ValidationError(
                    "Proposal yang sudah diajukan/disetujui tidak bisa dihapus!"
                )
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.anggaran <= 0:
                raise ValidationError("Anggaran harus diisi sebelum mengajukan proposal!")
            if not record.ketua_panitia_id:
                raise ValidationError("Tentukan Ketua Panitia sebelum mengajukan proposal!")
            vals = {'state': 'submitted'}
            if not record.tanggal_masuk:
                vals['tanggal_masuk'] = today
            record.write(vals)

    def _ensure_manager(self):
        if not self.env.user.has_group('campus_core.group_campus_lecturer'):
            raise AccessError(
                "Hanya Dosen (Lecturer) yang dapat menyetujui atau menolak "
                "proposal. Mahasiswa hanya dapat mengajukan proposal."
            )

    def action_approve(self):
        self._ensure_manager()
        today = fields.Date.context_today(self)
        for record in self:
            vals = {'state': 'approved'}
            if not record.tanggal_disetujui:
                vals['tanggal_disetujui'] = today
            # Nomor resmi dibuat sekali (saat pertama kali disetujui)
            if not record.name or record.name == 'New':
                no_keg = record._next_no_kegiatan()
                bulan = record.tanggal_masuk or today
                tahun = (record.tanggal_disetujui or today).year
                vals['no_kegiatan'] = no_keg
                vals['name'] = record._build_nomor(no_keg, bulan, tahun)
            record.write(vals)

    def action_reject(self):
        self._ensure_manager()
        self.write({'state': 'rejected'})

    def action_reset(self):
        self.write({'state': 'draft'})


class CampusProposalPanitia(models.Model):
    _name = 'campus.proposal.panitia'
    _description = 'Struktur Kepanitiaan Proposal Kegiatan'

    proposal_id = fields.Many2one(
        'campus.proposal', string='Proposal', required=True, ondelete='cascade',
    )
    mahasiswa_id = fields.Many2one(
        'campus.mahasiswa', string='Mahasiswa', required=True, ondelete='restrict',
    )
    divisi_id = fields.Many2one(
        'campus.divisi', string='Divisi', ondelete='restrict',
    )
    divisi_is_bph = fields.Boolean(
        related='divisi_id.is_bph', readonly=True,
    )
    jabatan_id = fields.Many2one(
        'campus.jabatan.panitia', string='Jabatan', required=True, ondelete='restrict',
    )

    @api.onchange('divisi_id')
    def _onchange_divisi_id(self):
        # Reset jabatan secara real-time bila tidak sesuai kategori divisi baru
        # (divisi BPH -> jabatan BPH, divisi biasa -> jabatan non-BPH).
        if self.jabatan_id and self.jabatan_id.is_bph != bool(self.divisi_id.is_bph):
            self.jabatan_id = False

    @api.constrains('mahasiswa_id', 'proposal_id')
    def _check_duplicate_panitia(self):
        for record in self:
            duplikat = self.search_count([
                ('id', '!=', record.id),
                ('proposal_id', '=', record.proposal_id.id),
                ('mahasiswa_id', '=', record.mahasiswa_id.id),
            ])
            if duplikat:
                raise ValidationError(
                    "Mahasiswa sudah terdaftar dalam kepanitiaan proposal ini!"
                )

    @api.constrains('divisi_id', 'jabatan_id')
    def _check_jabatan_divisi(self):
        for record in self:
            if record.jabatan_id and record.jabatan_id.is_bph != bool(record.divisi_id.is_bph):
                raise ValidationError(
                    "Jabatan '%s' tidak sesuai dengan divisi '%s'. "
                    "Divisi BPH hanya untuk jabatan BPH, dan sebaliknya."
                    % (record.jabatan_id.name,
                       record.divisi_id.name or '(kosong)')
                )
