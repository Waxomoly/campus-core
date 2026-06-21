from odoo import models, fields, api

# Ambang batas minimal kehadiran (%)
BATAS_KEHADIRAN = 75.0


class CampusMahasiswa(models.Model):
    _inherit = 'campus.mahasiswa'

    attendance_line_ids = fields.One2many(
        'campus.attendance.line', 'mahasiswa_id', string='Riwayat Absensi',
    )
    attendance_count = fields.Integer(
        string='Jumlah Absensi', compute='_compute_kehadiran',
    )
    persentase_kehadiran = fields.Float(
        string='Persentase Kehadiran (%)', compute='_compute_kehadiran', digits=(5, 2),
    )
    warning_kehadiran = fields.Boolean(
        string='Kehadiran Kurang', compute='_compute_kehadiran',
    )

    @api.depends('attendance_line_ids.status')
    def _compute_kehadiran(self):
        for record in self:
            total = len(record.attendance_line_ids)
            hadir = len(record.attendance_line_ids.filtered(lambda l: l.status == 'hadir'))
            record.attendance_count = total
            record.persentase_kehadiran = (hadir / total * 100) if total else 0.0
            record.warning_kehadiran = total > 0 and record.persentase_kehadiran < BATAS_KEHADIRAN

    def action_view_attendance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Riwayat Absensi',
            'res_model': 'campus.attendance.line',
            'view_mode': 'list',
            'domain': [('mahasiswa_id', '=', self.id)],
        }
