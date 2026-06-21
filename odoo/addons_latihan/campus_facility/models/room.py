from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CampusRoomType(models.Model):
    _name = 'campus.room.type'
    _description = 'Master Tipe Ruangan'
    _order = 'name'

    name = fields.Char(string='Nama Tipe', required=True)
    code_prefix = fields.Char(string='Prefix Kode', required=True, help="Contoh: ELK, FUR, ALT")

    active = fields.Boolean(string='Active', default=True)

    _name_unique = models.Constraint('unique(name)', 'Nama tipe fasilitas sudah ada!')
    _prefix_unique = models.Constraint('unique(code_prefix)', 'Prefix kode sudah digunakan!')

class CampusRoom(models.Model):
    _name = 'campus.room'
    _description = 'Data Ruangan'
    _order = 'name'

    kode = fields.Char(string='Kode Ruangan', required=True, copy=False, index=True, default='/')
    name = fields.Char(string='Nama Ruangan', required=True)

    tipe_id = fields.Many2one('campus.room.type', string='Tipe Ruangan', required=True)

    kapasitas = fields.Integer(string='Kapasitas', default=0, required=True)
    state = fields.Selection([
        ('tersedia', 'Tersedia'),
        ('maintenance', 'Maintenance'),
    ], string='Kondisi', default='tersedia', required=True, readonly=True, copy=False)
    booking_ids = fields.One2many(
        'campus.room.booking', 'room_id', string='Daftar Booking',
    )
    booking_count = fields.Integer(
        string='Jumlah Booking', compute='_compute_booking_count',
    )

    _kode_unique = models.Constraint('unique(kode)', 'Kode ruangan sudah ada!')

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for record in self:
            record.booking_count = len(record.booking_ids)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('kode', '/') == '/':
                # Ambil record tipe berdasarkan tipe_id yang dipilih
                tipe = self.env['campus.room.type'].browse(vals.get('tipe_id'))
                if tipe:
                    prefix = (tipe.code_prefix or 'FAC').upper()

                    # Buat kode sequence unik berdasarkan prefix, misal: 'campus.room.lab'
                    seq_code = f'campus.room.{prefix.lower()}'

                    # Coba minta angka selanjutnya dari database
                    sequence = self.env['ir.sequence'].next_by_code(seq_code)

                    # Jika sequence untuk tipe ini BELUM ADA, kita buatkan otomatis secara on-the-fly!
                    if not sequence:
                        self.env['ir.sequence'].sudo().create({
                            'name': f'Sequence Ruangan - {tipe.name}',
                            'code': seq_code,
                            'padding': 5,
                            'company_id': False,
                        })
                        # Panggil lagi setelah dibuat
                        sequence = self.env['ir.sequence'].next_by_code(seq_code)

                    vals['kode'] = f"{prefix}-{sequence}"
                else:
                    raise ValidationError("Tipe Ruangan harus dipilih untuk membuat kode!")
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
            'res_model': 'campus.room.booking',
            'view_mode': 'list,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }
