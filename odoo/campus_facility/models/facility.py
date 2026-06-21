from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CampusFacilityType(models.Model):
    _name = 'campus.facility.type'
    _description = 'Master Tipe Fasilitas'
    _order = 'name'

    name = fields.Char(string='Nama Tipe', required=True)
    code_prefix = fields.Char(string='Prefix Kode', required=True, help="Contoh: LAB, KLS, AULA")

    active = fields.Boolean(string='Active', default=True)

    _name_unique = models.Constraint('unique(name)', 'Nama tipe fasilitas sudah ada!')
    _prefix_unique = models.Constraint('unique(code_prefix)', 'Prefix kode sudah digunakan!')

class CampusFacility(models.Model):
    _name = 'campus.facility'
    _description = 'Data Fasilitas'
    _order = 'name'

    kode = fields.Char(string='Kode Fasilitas', required=True, copy=False, index=True, default='/')
    name = fields.Char(string='Nama Fasilitas', required=True)
    kuantitas = fields.Integer(string='Kuantitas', default=1, required=True)

    tipe_id = fields.Many2one('campus.facility.type', string='Tipe Fasilitas', required=True)

    state = fields.Selection([
        ('tersedia', 'Tersedia'),
        ('maintenance', 'Maintenance'),
    ], string='Kondisi', default='tersedia', required=True, readonly=True, copy=False)

    status_realtime = fields.Char(string='Status', compute='_compute_ketersediaan_sekarang')

    booking_ids = fields.One2many(
        'campus.facility.booking', 'facility_id', string='Daftar Booking',
    )
    booking_count = fields.Integer(
        string='Jumlah Booking', compute='_compute_booking_count',
    )

    _kode_unique = models.Constraint('unique(kode)', 'Kode fasilitas sudah ada!')
    _name_unique = models.Constraint('unique(name)', 'Nama fasilitas sudah ada!')
    _kuantitas_positive = models.Constraint('CHECK(kuantitas > 0)', 'Kuantitas harus lebih dari 0!')

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for record in self:
            record.booking_count = len(record.booking_ids)

    @api.constrains('kuantitas')
    def _check_kuantitas(self):
        for record in self:
            if record.kuantitas < 0:
                raise ValidationError("Kuantitas harus lebih besar atau sama dengan 0!")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('kode', '/') == '/':
                # Ambil record tipe berdasarkan tipe_id yang dipilih
                tipe = self.env['campus.facility.type'].browse(vals.get('tipe_id'))
                if tipe:
                    prefix = (tipe.code_prefix or 'FAC').upper()

                    # Buat kode sequence unik berdasarkan prefix, misal: 'campus.facility.lab'
                    seq_code = f'campus.facility.{prefix.lower()}'

                    # Coba minta angka selanjutnya dari database
                    sequence = self.env['ir.sequence'].next_by_code(seq_code)

                    # Jika sequence untuk tipe ini BELUM ADA, kita buatkan otomatis secara on-the-fly!
                    if not sequence:
                        self.env['ir.sequence'].sudo().create({
                            'name': f'Sequence Fasilitas - {tipe.name}',
                            'code': seq_code,
                            'padding': 5,
                            'company_id': False,
                        })
                        # Panggil lagi setelah dibuat
                        sequence = self.env['ir.sequence'].next_by_code(seq_code)

                    vals['kode'] = f"{prefix}-{sequence}"
                else:
                    raise ValidationError("Tipe fasilitas harus dipilih untuk membuat kode!")
        return super().create(vals_list)

    # Workflow maintenance request
    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_set_available(self):
        self.write({'state': 'tersedia'})

    def action_view_booking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Booking',
            'res_model': 'campus.facility.booking',
            'view_mode': 'list,form',
            'domain': [('facility_id', '=', self.id)],
            'context': {'default_facility_id': self.id},
        }

    def _compute_ketersediaan_sekarang(self):

        for record in self:
            if record.state == 'maintenance':
                record.status_realtime = 'Maintenance'
                continue

            record.status_realtime = 'Tersedia'
