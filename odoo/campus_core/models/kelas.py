from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

# Status KRS yang dianggap "mengunci" / memakai kuota kelas (FCFS)
KRS_LOCKED_STATES = ('submitted', 'processed')

HARI_SELECTION = [
    ('senin', 'Senin'),
    ('selasa', 'Selasa'),
    ('rabu', 'Rabu'),
    ('kamis', 'Kamis'),
    ('jumat', "Jumat"),
    ('sabtu', 'Sabtu'),
]


class CampusKelas(models.Model):
    """Kelas perkuliahan (offering) untuk sebuah mata kuliah.

    Membedakan jadwal & kuota antar kelas (Kelas A, B, C, ...).
    """
    _name = 'campus.kelas'
    _description = 'Kelas Mata Kuliah'
    _order = 'mata_kuliah_id, name'
    _rec_names_search = ['name', 'mata_kuliah_id']

    name = fields.Char(string='Kelas', required=True, help='Contoh: A, B, C')
    mata_kuliah_id = fields.Many2one(
        'campus.mata_kuliah', string='Mata Kuliah',
        required=True, ondelete='cascade', index=True,
    )
    semester = fields.Selection(
        selection='_get_semester_selection',
        string='Semester',
        required=True,
        default=lambda self: self._default_semester(),
    )
    dosen_id = fields.Many2one(
        'campus.dosen',
        string='Dosen Pengampu',
        ondelete='restrict',
    )

    sks = fields.Integer(
        string='SKS', related='mata_kuliah_id.sks', store=True, readonly=True,
    )

    # ---- Jadwal ----
    hari = fields.Selection(HARI_SELECTION, string='Hari', required=True)
    jam_mulai = fields.Float(
        string='Jam Mulai', required=True, help='Format 24 jam (mis. 8.5 = 08:30)',
    )
    jam_selesai = fields.Float(string='Jam Selesai', required=True)
    ruangan = fields.Char(string='Ruangan')

    # ---- Kuota (FCFS) ----
    kuota = fields.Integer(string='Kuota Maksimal', default=40, required=True)
    terisi = fields.Integer(
        string='Terisi', compute='_compute_kuota', store=True,
    )
    sisa_kuota = fields.Integer(
        string='Sisa Kuota', compute='_compute_kuota', store=True,
    )
    is_available = fields.Boolean(
        string='Tersedia', compute='_compute_kuota', store=True,
        help='True jika masih ada sisa kuota.',
    )
    krs_line_ids = fields.One2many(
        'campus.krs.line', 'kelas_id', string='Peserta KRS',
    )

    _kuota_positive = models.Constraint(
        'CHECK(kuota > 0)', 'Kuota kelas harus lebih besar dari 0!')

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends(
        'kuota',
        'krs_line_ids.state',
        'krs_line_ids.krs_state',
    )
    def _compute_kuota(self):
        for record in self:
            terisi = len(record.krs_line_ids.filtered(
                lambda l: l.krs_state in KRS_LOCKED_STATES and l.state != 'rejected'
            ))
            record.terisi = terisi
            record.sisa_kuota = record.kuota - terisi
            record.is_available = (record.kuota - terisi) > 0

    @api.depends('name', 'mata_kuliah_id.name', 'hari', 'jam_mulai', 'jam_selesai')
    def _compute_display_name(self):
        for record in self:
            mk = record.mata_kuliah_id.name or ''
            label = "%s - Kelas %s" % (mk, record.name or '')
            if record.hari:
                hari = dict(HARI_SELECTION).get(record.hari, record.hari)
                label += " (%s %s-%s)" % (
                    hari,
                    record._format_jam(record.jam_mulai),
                    record._format_jam(record.jam_selesai),
                )
            record.display_name = label

    @api.model
    def _get_semester_selection(self):
        current = date.today().year

        result = []

        for year in range(current - 1, current + 5):
            result.append((
                f'Gasal {year}/{year + 1}',
                f'Gasal {year}/{year + 1}',
            ))
            result.append((
                f'Genap {year}/{year + 1}',
                f'Genap {year}/{year + 1}',
            ))

        return result

    @api.model
    def _default_semester(self):
        today = date.today()

        if today.month >= 8:
            return f'Gasal {today.year}/{today.year + 1}'

        return f'Genap {today.year - 1}/{today.year}'

    @staticmethod
    def _format_jam(value):
        jam = int(value)
        menit = int(round((value - jam) * 60))
        return "%02d:%02d" % (jam, menit)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('jam_mulai', 'jam_selesai')
    def _check_jam(self):
        for record in self:
            if not (0 <= record.jam_mulai < 24) or not (0 < record.jam_selesai <= 24):
                raise ValidationError("Jam harus berada di rentang 0-24!")
            if record.jam_selesai <= record.jam_mulai:
                raise ValidationError(
                    "Jam Selesai harus lebih besar dari Jam Mulai pada kelas %s!"
                    % (record.display_name,)
                )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def is_bentrok_with(self, other):
        """Return True jika kelas ini bentrok jadwal dengan kelas `other`."""
        self.ensure_one()
        if not other or other == self:
            return False
        if self.hari != other.hari:
            return False
        # Dua interval [a,b) dan [c,d) bentrok jika a < d dan c < b
        return (self.jam_mulai < other.jam_selesai
                and other.jam_mulai < self.jam_selesai)
