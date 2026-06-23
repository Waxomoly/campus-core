from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CampusAttendanceSession(models.Model):
    _name = 'campus.attendance.session'
    _description = 'Sesi Absensi'
    _order = 'tanggal desc'

    name = fields.Char(
        string='Nama Sesi', compute='_compute_name', store=True,
        readonly=True, default='Draft',
    )
    kelas_domain = fields.Char(compute='_compute_kelas_domain')
    kelas_id = fields.Many2one(
        'campus.kelas',
        string='Kelas',
        required=True,
        ondelete='restrict',
    )
    tanggal = fields.Date(string='Tanggal', required=True, default=fields.Date.context_today)
    pertemuan = fields.Integer(string='Pertemuan Ke', default=1, required=True)
    line_ids = fields.One2many(
        'campus.attendance.line', 'session_id', string='Daftar Hadir',
    )
    jumlah_hadir = fields.Integer(string='Jumlah Hadir', compute='_compute_statistik', store=True)
    jumlah_mahasiswa = fields.Integer(string='Total Mahasiswa', compute='_compute_statistik', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', required=True, readonly=True, copy=False)

    @api.depends_context('uid')
    def _compute_kelas_domain(self):
        is_manager = self.env.user.has_group('campus_attendance.group_attendance_manager')
        for record in self:
            if is_manager:
                record.kelas_domain = '[]'
            else:
                record.kelas_domain = f"[('dosen_id.user_id', '=', {self.env.uid})]"

    @api.depends('kelas_id.mata_kuliah_id.kode_mk', 'pertemuan')
    def _compute_name(self):
        for record in self:
            if record.kelas_id:
                record.name = "ABS/%s/%s/P%s" % (
                    record.kelas_id.mata_kuliah_id.kode_mk,
                    record.kelas_id.name,
                    record.pertemuan,
                )
            else:
                record.name = 'Draft'

    @api.depends('line_ids.status')
    def _compute_statistik(self):
        for record in self:
            record.jumlah_mahasiswa = len(record.line_ids)
            record.jumlah_hadir = len(record.line_ids.filtered(lambda l: l.status == 'hadir'))

    @api.constrains('line_ids')
    def _check_duplicate_mahasiswa(self):
        for record in self:
            mhs = record.line_ids.mapped('mahasiswa_id')
            if len(mhs) != len(set(mhs.ids)):
                raise ValidationError(
                    "Mahasiswa tidak boleh diabsen lebih dari sekali dalam satu sesi!"
                )

    def unlink(self):
        for record in self:
            if record.state == 'confirmed':
                raise ValidationError("Sesi yang sudah Confirmed tidak bisa dihapus!")
        return super().unlink()

    # Workflow + validation
    def action_confirm(self):
        for record in self:
            if not record.line_ids:
                raise ValidationError("Isi daftar hadir terlebih dahulu sebelum konfirmasi!")
            record.state = 'confirmed'

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_generate_attendance(self):
        self.ensure_one()

        if self.state == 'confirmed':
            raise ValidationError(
                "Absensi yang sudah Confirmed tidak dapat digenerate ulang!"
            )
        if not self.kelas_id:
            raise ValidationError(
                "Pilih kelas terlebih dahulu!"
            )

        self.line_ids.unlink()

        krs_lines = self.env['campus.krs.line'].search([
            ('kelas_id', '=', self.kelas_id.id),
            ('krs_state', '=', 'processed'),
            ('state', '=', 'approved'),
        ])

        vals = []

        for line in krs_lines:
            vals.append((0, 0, {
                'mahasiswa_id': line.krs_id.mahasiswa_id.id,
                'status': 'alpha',
            }))

        self.line_ids = vals



class CampusAttendanceLine(models.Model):
    _name = 'campus.attendance.line'
    _description = 'Detail Kehadiran Mahasiswa'

    kelas_id = fields.Many2one(related='session_id.kelas_id', store=True, string='Kelas')
    mata_kuliah_id = fields.Many2one(related='session_id.kelas_id.mata_kuliah_id', store=True, string='Mata Kuliah')
    pertemuan = fields.Integer(related='session_id.pertemuan', store=True, string='Pertemuan Ke')
    session_id = fields.Many2one(
        'campus.attendance.session', string='Sesi', required=True, ondelete='cascade',
    )
    mahasiswa_id = fields.Many2one(
        'campus.mahasiswa', string='Mahasiswa', required=True, ondelete='restrict',
    )
    status = fields.Selection([
        ('hadir', 'Hadir'),
        ('izin', 'Izin'),
        ('sakit', 'Sakit'),
        ('alpha', 'Alpha'),
    ], string='Status', default='hadir', required=True)
    keterangan = fields.Char(string='Keterangan')

    is_hadir = fields.Integer(compute='_compute_status_int', store=True)
    is_izin = fields.Integer(compute='_compute_status_int', store=True)
    is_sakit = fields.Integer(compute='_compute_status_int', store=True)
    is_alpha = fields.Integer(compute='_compute_status_int', store=True)

    @api.depends('status')
    def _compute_status_int(self):
        for record in self:
            record.is_hadir = 1 if record.status == 'hadir' else 0
            record.is_izin = 1 if record.status == 'izin' else 0
            record.is_sakit = 1 if record.status == 'sakit' else 0
            record.is_alpha = 1 if record.status == 'alpha' else 0

    @api.onchange('status')
    def _onchange_status(self):
        if self.status in ('izin', 'sakit') and not self.keterangan:
            return {
                'warning': {
                    'title': 'Keterangan Diperlukan',
                    'message': 'Mohon isi keterangan untuk status Izin / Sakit.',
                }
            }