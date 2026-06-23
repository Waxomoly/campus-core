from odoo import models, fields, api
from odoo.exceptions import ValidationError

nilai_bobot = {
    'A': 4.0,
    'B+': 3.5,
    'B': 3.0,
    'C+': 2.5,
    'C': 2.0,
    'D': 1.0,
    'E': 0.0,
}
# syarat kelulusan
sks_lulus = 144
ipk_minimal = 2.0


def angka_ke_huruf(nilai_angka):
    # konversi nilai angka ke huruf
    if nilai_angka >= 85:
        return 'A'
    elif nilai_angka >= 80:
        return 'B+'
    elif nilai_angka >= 75:
        return 'B'
    elif nilai_angka >= 70:
        return 'C+'
    elif nilai_angka >= 60:
        return 'C'
    elif nilai_angka >= 50:
        return 'D'
    return 'E'


class CampusTranskrip(models.Model):
    _name = 'campus.transkrip'
    _description = 'Transkrip Nilai Mahasiswa'
    _order = 'create_date desc'

    name = fields.Char(
        string='Nomor Transkrip', compute='_compute_name',
        store=True, readonly=True, default='Draft',
    )
    mahasiswa_id = fields.Many2one(
        'campus.mahasiswa', string='Mahasiswa',
        required=True, ondelete='cascade',
    )

    nilai_ids = fields.One2many(
        'campus.transkrip.nilai', 'transkrip_id', string='Daftar Nilai',
    )

    total_sks = fields.Integer(string='Total SKS', compute='_compute_ipk', store=True)

    total_mutu = fields.Float(string='Total Nilai Mutu', compute='_compute_ipk', store=True)

    ipk = fields.Float(string='IPK', compute='_compute_ipk', store=True, digits=(3, 2))

    status_kelulusan = fields.Selection([
        ('belum', 'Belum Lulus'),
        ('lulus', 'Lulus'),
    ], string='Status Kelulusan', compute='_compute_status', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', required=True, readonly=True, copy=False)

    @api.depends('mahasiswa_id.nim')
    def _compute_name(self):
        for record in self:
            if record.mahasiswa_id:
                record.name = "TR/%s" % (record.mahasiswa_id.nim)
            else:
                record.name = 'Draft'

    @api.depends('nilai_ids.sks', 'nilai_ids.nilai_mutu')
    def _compute_ipk(self):
        for record in self:
            total_sks = sum(record.nilai_ids.mapped('sks'))
            total_mutu = sum(record.nilai_ids.mapped('nilai_mutu'))
            record.total_sks = total_sks
            record.total_mutu = total_mutu
            record.ipk = (total_mutu / total_sks) if total_sks else 0.0

    @api.depends('ipk', 'total_sks')
    def _compute_status(self):
        for record in self:
            lulus = record.ipk >= ipk_minimal and record.total_sks >= sks_lulus
            record.status_kelulusan = 'lulus' if lulus else 'belum'


    # Constrains
    @api.constrains('nilai_ids')
    def _check_duplicate_mk(self):
        for record in self:
            mk_ids = [line.mata_kuliah_id.id for line in record.nilai_ids if line.mata_kuliah_id]

            if len(mk_ids) != len(set(mk_ids)):
                raise ValidationError(
                    "Mata kuliah tidak boleh duplikat dalam satu transkrip!"
                )

    @api.constrains('mahasiswa_id')
    def _check_unique_mahasiswa(self):
        for record in self:
            duplicate = self.search([
                ('mahasiswa_id', '=', record.mahasiswa_id.id),
                ('id', '!=', record.id)
            ])
            if duplicate:
                raise ValidationError(
                    "Mahasiswa ini sudah memiliki dokumen transkrip! "
                    "Hanya boleh ada 1 transkrip per mahasiswa."
                )

    # Override method
    # transkrip yang "approved" tidak bisa di edit
    def write(self, vals):
        for record in self:
            editing_other = set(vals) - {'state'}
            if record.state == 'approved' and editing_other:
                raise ValidationError(
                    "Transkrip yang sudah Approved tidak bisa diubah!"
                )
        return super().write(vals)

    # transkrip yang "approved" tidak bisa di delete
    def unlink(self):
        for record in self:
            if record.state == 'approved':
                raise ValidationError(
                    "Transkrip yang sudah Approved tidak bisa dihapus!"
                )
        return super().unlink()


    # Workflow (Draft -> Submitted -> Approved)
    def action_submit(self):
        for record in self:
            if not record.nilai_ids:
                raise ValidationError(
                    "Tambahkan minimal satu nilai sebelum submit transkrip!"
                )
            record.state = 'submitted'

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reset(self):
        self.write({'state': 'draft'})

    # mengambil MK di KRS yang approved
    def action_sync_krs(self):
        for record in self:
            if record.state == 'approved':
                raise ValidationError("Transkrip yang sudah Lulus tidak bisa ditarik datanya lagi!")

            if not record.mahasiswa_id:
                raise ValidationError("Pilih mahasiswa terlebih dahulu!")

            # cari semua KRS yang sudah diproses
            krs_lines = self.env['campus.krs.line'].search([
                ('krs_id.mahasiswa_id', '=', record.mahasiswa_id.id),
                ('krs_id.state', '=', 'processed'),
                ('state', '=', 'approved')
            ])

            # agar MK lama tidak terhapus
            existing_course_ids = record.nilai_ids.mapped('mata_kuliah_id.id')

            command_list = []
            for line in krs_lines:
                course_id = line.mata_kuliah_id.id
                if course_id not in existing_course_ids:
                    command_list.append((0, 0, {
                        'mata_kuliah_id': course_id,
                        'nilai_angka': 0.0,
                    }))
                    existing_course_ids.append(course_id)

            if command_list:
                record.write({'nilai_ids': command_list})
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Info',
                        'message': 'Tidak ada mata kuliah baru dari KRS untuk ditarik.',
                        'type': 'info',
                        'sticky': False,
                    }
                }

    # fetch data KRS ketika memilih mahasiswa
    @api.onchange('mahasiswa_id')
    def _onchange_mahasiswa_id_fetch_courses(self):
        if not self.mahasiswa_id:
            self.nilai_ids = [(5, 0, 0)]
            return

        krs_lines = self.env['campus.krs.line'].search([
            ('krs_id.mahasiswa_id', '=', self.mahasiswa_id.id),
            ('krs_id.state', '=', 'processed'),
            ('state', '=', 'approved')
        ])

        unique_courses = {}
        for line in krs_lines:
            course_id = line.mata_kuliah_id.id
            if course_id not in unique_courses:
                unique_courses[course_id] = {
                    'mata_kuliah_id': course_id,
                    'nilai_angka': 0.0,
                }

        command_list = [(5, 0, 0)]
        for vals in unique_courses.values():
            command_list.append((0, 0, vals))

        self.nilai_ids = command_list

class CampusTranskripNilai(models.Model):
    _name = 'campus.transkrip.nilai'
    _description = 'Detail Nilai Transkrip'

    transkrip_id = fields.Many2one(
        'campus.transkrip', string='Transkrip',
        required=True, ondelete='cascade',
    )

    mata_kuliah_id = fields.Many2one(
        'campus.mata_kuliah', string='Mata Kuliah', required=True,
    )
    sks = fields.Integer(
        string='SKS', related='mata_kuliah_id.sks', store=True, readonly=True,
    )
    nilai_angka = fields.Float(string='Nilai Angka', default=0.0, required=True)

    nilai_huruf = fields.Char(
        string='Nilai', compute='_compute_nilai_huruf', store=True,
    )
    bobot = fields.Float(string='Bobot', compute='_compute_nilai_huruf', store=True)

    nilai_mutu = fields.Float(
        string='Nilai Mutu', compute='_compute_mutu', store=True,
    )

    is_lulus = fields.Boolean(
        string='Lulus MK', compute='_compute_nilai_huruf', store=True,
    )
    _nilai_range = models.Constraint(
        'CHECK(nilai_angka >= 0 AND nilai_angka <= 100)',
        'Nilai angka harus berada di rentang 0 - 100!')

    @api.constrains('nilai_angka')
    def _check_nilai_angka(self):
        for record in self:
            if not (0 <= record.nilai_angka <= 100):
                raise ValidationError("Nilai angka harus di rentang 0 - 100!")

    @api.depends('nilai_angka')
    def _compute_nilai_huruf(self):
        for record in self:
            huruf = angka_ke_huruf(record.nilai_angka)
            record.nilai_huruf = huruf
            record.bobot = nilai_bobot.get(huruf, 0.0)
            record.is_lulus = huruf != 'E'

    @api.depends('bobot', 'sks')
    def _compute_mutu(self):
        for record in self:
            record.nilai_mutu = record.bobot * record.sks

    # onchange: peringatan jika nilai tidak lulus (E)
    @api.onchange('nilai_angka')
    def _onchange_nilai_angka(self):
        if self.nilai_angka and self.nilai_angka < 50:
            return {
                'warning': {
                    'title': 'Perhatian',
                    'message': 'Nilai di bawah 50 (E) berarti tidak lulus '
                               'mata kuliah ini.',
                }
            }

