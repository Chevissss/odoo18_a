from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from pytz import timezone


class Reserva(models.Model):
    _name = 'reserva.reserva'
    _description = 'Reserva de Cancha'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'fecha_inicio desc'

    name = fields.Char(
        string='Número de Reserva',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo')
    )
    
    # Relaciones principales
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True,
        default=lambda self: self.env.user.partner_id
    )
    cancha_id = fields.Many2one(
        'reserva.cancha',
        string='Cancha',
        required=True,
        tracking=True,
        domain=[('activa', '=', True)]
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    # Fechas y horarios
    fecha_inicio = fields.Datetime(
        string='Fecha y Hora Inicio',
        required=True,
        tracking=True
    )
    fecha_fin = fields.Datetime(
        string='Fecha y Hora Fin',
        required=True,
        tracking=True
    )
    duracion = fields.Float(
        string='Duración (horas)',
        compute='_compute_duracion',
        store=True
    )
    
    # Estado
    state = fields.Selection([
        ('borrador', 'Borrador'),
        ('pendiente', 'Pendiente Confirmación'),
        ('confirmada', 'Confirmada'),
        ('en_curso', 'En Curso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('no_show', 'No Show')
    ], string='Estado', default='borrador', required=True, tracking=True)
    
    # Información adicional
    numero_jugadores = fields.Integer(string='Número de Jugadores')
    notas = fields.Text(string='Notas')
    motivo_cancelacion = fields.Text(string='Motivo de Cancelación')
    
    # Precios
    precio_hora = fields.Float(
        string='Precio por Hora',
        related='cancha_id.precio_hora',
        store=True
    )
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_totales',
        store=True
    )
    descuento = fields.Float(
        string='Descuento (%)',
        default=0.0
    )
    monto_descuento = fields.Float(
        string='Monto Descuento',
        compute='_compute_totales',
        store=True
    )
    total = fields.Float(
        string='Total',
        compute='_compute_totales',
        store=True
    )
    
    # Pago
    pagado = fields.Boolean(string='Pagado', tracking=True)
    metodo_pago = fields.Selection([
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('online', 'Pago Online')
    ], string='Método de Pago')
    
    # Control de tiempos
    fecha_creacion = fields.Datetime(
        string='Fecha Creación',
        default=fields.Datetime.now,
        readonly=True
    )
    fecha_confirmacion = fields.Datetime(string='Fecha Confirmación', readonly=True)
    fecha_cancelacion = fields.Datetime(string='Fecha Cancelación', readonly=True)
    
    # Campos computados
    puede_cancelar = fields.Boolean(
        string='Puede Cancelar',
        compute='_compute_puede_cancelar'
    )
    puede_editar = fields.Boolean(
        string='Puede Editar',
        compute='_compute_puede_editar'
    )
    es_pasada = fields.Boolean(
        string='Es Pasada',
        compute='_compute_es_pasada'
    )
    color = fields.Integer(string='Color', compute='_compute_color')

    _sql_constraints = [
        ('fecha_check', 'CHECK(fecha_fin > fecha_inicio)', 
         'La fecha de fin debe ser posterior a la fecha de inicio!')
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nuevo')) == _('Nuevo'):
            vals['name'] = self.env['ir.sequence'].next_by_code('reserva.reserva') or _('Nuevo')
        return super().create(vals)

    @api.depends('fecha_inicio', 'fecha_fin')
    def _compute_duracion(self):
        for reserva in self:
            if reserva.fecha_inicio and reserva.fecha_fin:
                delta = reserva.fecha_fin - reserva.fecha_inicio
                reserva.duracion = delta.total_seconds() / 3600
            else:
                reserva.duracion = 0.0

    @api.depends('duracion', 'precio_hora', 'descuento')
    def _compute_totales(self):
        for reserva in self:
            reserva.subtotal = reserva.duracion * reserva.precio_hora
            reserva.monto_descuento = reserva.subtotal * (reserva.descuento / 100)
            reserva.total = reserva.subtotal - reserva.monto_descuento

    @api.depends('fecha_inicio', 'state')
    def _compute_puede_cancelar(self):
        for reserva in self:
            if reserva.state in ['cancelada', 'completada', 'no_show']:
                reserva.puede_cancelar = False
            else:
                # Permite cancelar hasta 2 horas antes
                if reserva.fecha_inicio:
                    ahora = fields.Datetime.now()
                    limite = reserva.fecha_inicio - timedelta(hours=2)
                    reserva.puede_cancelar = ahora < limite
                else:
                    reserva.puede_cancelar = True

    @api.depends('state', 'fecha_inicio')
    def _compute_puede_editar(self):
        for reserva in self:
            if reserva.state in ['cancelada', 'completada', 'no_show']:
                reserva.puede_editar = False
            else:
                ahora = fields.Datetime.now()
                reserva.puede_editar = not reserva.fecha_inicio or ahora < reserva.fecha_inicio

    @api.depends('fecha_inicio')
    def _compute_es_pasada(self):
        ahora = fields.Datetime.now()
        for reserva in self:
            reserva.es_pasada = reserva.fecha_inicio < ahora if reserva.fecha_inicio else False

    @api.depends('state')
    def _compute_color(self):
        colores = {
            'borrador': 4,      # Azul
            'pendiente': 2,     # Naranja
            'confirmada': 10,   # Verde
            'en_curso': 7,      # Verde claro
            'completada': 3,    # Amarillo
            'cancelada': 1,     # Rojo
            'no_show': 9        # Fucsia
        }
        for reserva in self:
            reserva.color = colores.get(reserva.state, 0)

    @api.constrains('fecha_inicio', 'fecha_fin', 'cancha_id')
    def _check_validaciones(self):
        for reserva in self:
            # 1. No permitir reservas en el pasado
            if reserva.fecha_inicio < fields.Datetime.now() and reserva.state == 'borrador':
                raise ValidationError(_('No se pueden crear reservas con fecha en el pasado'))
            
            # 2. Validar duración mínima y máxima
            if reserva.duracion < 0.5:
                raise ValidationError(_('La duración mínima de una reserva es 30 minutos'))
            if reserva.duracion > 8:
                raise ValidationError(_('La duración máxima de una reserva es 8 horas'))
            
            # 3. Validar capacidad
            if reserva.numero_jugadores and reserva.numero_jugadores > reserva.cancha_id.capacidad:
                raise ValidationError(
                    _('El número de jugadores (%s) excede la capacidad de la cancha (%s)') % 
                    (reserva.numero_jugadores, reserva.cancha_id.capacidad)
                )
            
            # 4. Validar que no haya solapamiento con otras reservas
            if reserva.state != 'cancelada':
                solapadas = self.search([
                    ('id', '!=', reserva.id),
                    ('cancha_id', '=', reserva.cancha_id.id),
                    ('state', 'not in', ['cancelada', 'no_show']),
                    '|',
                        '&',
                            ('fecha_inicio', '<=', reserva.fecha_inicio),
                            ('fecha_fin', '>', reserva.fecha_inicio),
                        '&',
                            ('fecha_inicio', '<', reserva.fecha_fin),
                            ('fecha_fin', '>=', reserva.fecha_fin),
                ])
                if solapadas:
                    raise ValidationError(
                        _('Ya existe una reserva confirmada en ese horario.\nReserva conflictiva: %s') % 
                        solapadas[0].name
                    )
            
            # 5. Validar horario dentro del horario de operación
            if reserva.cancha_id.horario_ids:
                dia_semana = str(reserva.fecha_inicio.weekday())
                hora_inicio = reserva.fecha_inicio.hour + reserva.fecha_inicio.minute / 60
                hora_fin = reserva.fecha_fin.hour + reserva.fecha_fin.minute / 60
                
                horario_valido = reserva.cancha_id.horario_ids.filtered(
                    lambda h: h.dia_semana == dia_semana and 
                    h.hora_inicio <= hora_inicio and 
                    h.hora_fin >= hora_fin
                )
                
                if not horario_valido:
                    raise ValidationError(_('La reserva está fuera del horario de operación de la cancha'))
            
            # 6. Validar que las reservas se hagan con anticipación (min 1 hora)
            if reserva.state == 'borrador':
                ahora = fields.Datetime.now()
                minimo_anticipacion = ahora + timedelta(hours=1)
                if reserva.fecha_inicio < minimo_anticipacion:
                    raise ValidationError(_('Las reservas deben hacerse con al menos 1 hora de anticipación'))

    def action_view_partner(self):
            """
            Este método permite que el botón de estadística (stat button)
            en el formulario abra la ficha del cliente asociado.
            """
            self.ensure_one()
            return {
                'type': 'ir.actions.act_window',
                'name': _('Cliente'),
                'res_model': 'res.partner',
                'view_mode': 'form',
                'res_id': self.partner_id.id,
                'target': 'current',
            }

    def action_confirmar(self):
        for reserva in self:
            if reserva.state != 'borrador':
                raise UserError(_('Solo se pueden confirmar reservas en borrador'))
            reserva.write({
                'state': 'confirmada',
                'fecha_confirmacion': fields.Datetime.now()
            })
            reserva.message_post(body=_('Reserva confirmada'))
            # Enviar email de confirmación
            reserva._send_confirmation_email()

    def action_iniciar(self):
        for reserva in self:
            if reserva.state != 'confirmada':
                raise UserError(_('Solo se pueden iniciar reservas confirmadas'))
            reserva.write({'state': 'en_curso'})
            reserva.message_post(body=_('Reserva iniciada'))

    def action_completar(self):
        for reserva in self:
            if reserva.state != 'en_curso':
                raise UserError(_('Solo se pueden completar reservas en curso'))
            reserva.write({'state': 'completada'})
            reserva.message_post(body=_('Reserva completada'))

    def action_cancelar(self):
        for reserva in self:
            if not reserva.puede_cancelar:
                raise UserError(_('Esta reserva no puede ser cancelada'))
            return {
                'name': _('Cancelar Reserva'),
                'type': 'ir.actions.act_window',
                'res_model': 'reserva.cancelar.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_reserva_id': reserva.id}
            }

    def action_marcar_no_show(self):
        for reserva in self:
            reserva.write({
                'state': 'no_show',
                'fecha_cancelacion': fields.Datetime.now()
            })
            reserva.message_post(body=_('Cliente no se presentó'))

    def _send_confirmation_email(self):
        template = self.env.ref('reserva_canchas.email_template_reserva_confirmacion', 
                               raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    @api.model
    def _cron_actualizar_estados(self):
        """Cron para actualizar estados automáticamente"""
        ahora = fields.Datetime.now()
        
        # Marcar como "en curso" las reservas confirmadas que ya iniciaron
        reservas_iniciar = self.search([
            ('state', '=', 'confirmada'),
            ('fecha_inicio', '<=', ahora),
            ('fecha_fin', '>', ahora)
        ])
        reservas_iniciar.write({'state': 'en_curso'})
        
        # Completar automáticamente las reservas que ya terminaron
        reservas_completar = self.search([
            ('state', 'in', ['confirmada', 'en_curso']),
            ('fecha_fin', '<=', ahora)
        ])
        reservas_completar.write({'state': 'completada'})

    def _compute_access_url(self):
        super()._compute_access_url()
        for reserva in self:
            reserva.access_url = '/my/reservas/%s' % reserva.id