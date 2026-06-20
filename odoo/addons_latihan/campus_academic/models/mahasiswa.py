from odoo import models, fields, api


class CampusMahasiswa(models.Model):
    _inherit = 'campus.mahasiswa'

    transkrip_ids = fields.One2many(
        'campus.transkrip', 'mahasiswa_id', string='Transkrip',
    )
    transkrip_count = fields.Integer(
        string='Jumlah Transkrip', compute='_compute_transkrip_count',
    )

    # Perbaikan: store true
    ipk = fields.Float(
        string='IPK', compute='_compute_ipk_total', store=True, digits=(3, 2)
    )
    # Override field kelulusan dari campus_core agar dihitung otomatis
    # dari transkrip yang sudah Approved.
    total_sks_lulus = fields.Integer(
        compute='_compute_sks_lulus', store=True, readonly=True,
    )

    @api.depends('transkrip_ids')
    def _compute_transkrip_count(self):
        for record in self:
            record.transkrip_count = len(record.transkrip_ids)

    # PERBAIKAN
    @api.depends('transkrip_ids.ipk')
    def _compute_ipk_total(self):
        for record in self:
            # Karena 1 mahasiswa hanya memiliki 1 dokumen transkrip seumur hidup
            if record.transkrip_ids:
                # Mengambil nilai IPK langsung dari dokumen transkripnya (Draft/Approved)
                calculated_gpa = record.transkrip_ids[0].ipk
            else:
                calculated_gpa = 0.0

            record.ipk = calculated_gpa

    @api.depends(
        'transkrip_ids.state',
        'transkrip_ids.nilai_ids.is_lulus',
        'transkrip_ids.nilai_ids.sks',
    )
    def _compute_sks_lulus(self):
        for record in self:
            total = 0
            for transkrip in record.transkrip_ids.filtered(
                lambda t: t.state == 'approved'
            ):
                total += sum(transkrip.nilai_ids.filtered('is_lulus').mapped('sks'))
            record.total_sks_lulus = total

            # Perbaikan
            if total >= 144 and record.ipk >= 2.0:
                record.status_kelulusan = 'lulus'
            else:
                record.status_kelulusan = 'belum'

    def action_view_transkrip(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transkrip',
            'res_model': 'campus.transkrip',
            'view_mode': 'list,form',
            'domain': [('mahasiswa_id', '=', self.id)],
            'context': {'default_mahasiswa_id': self.id},
        }
