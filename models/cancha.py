from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Cancha(models.Model):
    _name = 'reserva.cancha'
    _description = 'Cancha Deportiva'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string='Nombre',
        required=True,
        tracking=True
    )
    code = fields.Char(
        string='Código',
        required=True,
        copy=False,
        tracking=True
    )
    sequence = fields.Integer(
        string='Secuencia',
        default=10
    )
    tipo_deporte = fields.Selection([
        ('futbol', 'Fútbol'),
        ('tenis', 'Tenis'),
        ('basquet', 'Básquetbol'),
        ('voley', 'Vóleibol'),
        ('paddle', 'Pádel'),
        ('otro', 'Otro')
    ], string='Tipo de Deporte', required=True, tracking=True)
    
    capacidad = fields.Integer(
        string='Capacidad (personas)',
        default=10,
        required=True
    )
    precio_hora = fields.Float(
        string='Precio por Hora',
        required=True,
        tracking=True
    )
    descripcion = fields.Text(string='Descripción')
    
    activa = fields.Boolean(
        string='Activa',
        default=True,
        tracking=True
    )
    disponible_web = fields.Boolean(
        string='Disponible en Web',
        default=True,
        help='Si está marcado, los usuarios pueden reservar desde el portal'
    )
    
    # Características
    tiene_techo = fields.Boolean(string='Techada')
    tiene_iluminacion = fields.Boolean(string='Iluminación')
    tiene_vestuarios = fields.Boolean(string='Vestuarios')
    tiene_estacionamiento = fields.Boolean(string='Estacionamiento')
    
    # Imágenes
    image_1920 = fields.Image(string='Imagen', max_width=1920, max_height=1920)
    image_128 = fields.Image(string='Imagen 128', related='image_1920', max_width=128, max_height=128, store=True)
    
    # Relaciones
    horario_ids = fields.One2many(
        'reserva.horario',
        'cancha_id',
        string='Horarios Disponibles'
    )
    reserva_ids = fields.One2many(
        'reserva.reserva',
        'cancha_id',
        string='Reservas'
    )
    
    # Estadísticas
    total_reservas = fields.Integer(
        string='Total Reservas',
        compute='_compute_estadisticas',
        store=True
    )
    ingresos_totales = fields.Float(
        string='Ingresos Totales',
        compute='_compute_estadisticas',
        store=True
    )
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'El código de la cancha debe ser único!')
    ]

    @api.depends('reserva_ids', 'reserva_ids.state', 'reserva_ids.total')
    def _compute_estadisticas(self):
        for cancha in self:
            reservas_confirmadas = cancha.reserva_ids.filtered(
                lambda r: r.state in ['confirmada', 'completada']
            )
            cancha.total_reservas = len(reservas_confirmadas)
            cancha.ingresos_totales = sum(reservas_confirmadas.mapped('total'))

    @api.constrains('capacidad', 'precio_hora')
    def _check_valores_positivos(self):
        for cancha in self:
            if cancha.capacidad <= 0:
                raise ValidationError(_('La capacidad debe ser mayor a 0'))
            if cancha.precio_hora <= 0:
                raise ValidationError(_('El precio debe ser mayor a 0'))

    def action_view_reservas(self):
        self.ensure_one()
        return {
            'name': _('Reservas de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'reserva.reserva',
            'view_mode': 'tree,form,calendar',
            'domain': [('cancha_id', '=', self.id)],
            'context': {'default_cancha_id': self.id}
        }