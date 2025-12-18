from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Horario(models.Model):
    _name = 'reserva.horario'
    _description = 'Horario de Operación de Cancha'
    _order = 'cancha_id, dia_semana, hora_inicio'

    cancha_id = fields.Many2one(
        'reserva.cancha',
        string='Cancha',
        required=True,
        ondelete='cascade'
    )
    
    dia_semana = fields.Selection([
        ('0', 'Lunes'),
        ('1', 'Martes'),
        ('2', 'Miércoles'),
        ('3', 'Jueves'),
        ('4', 'Viernes'),
        ('5', 'Sábado'),
        ('6', 'Domingo')
    ], string='Día de la Semana', required=True)
    
    hora_inicio = fields.Float(
        string='Hora Inicio',
        required=True,
        help='Formato 24 horas (ej: 8.5 = 08:30)'
    )
    
    hora_fin = fields.Float(
        string='Hora Fin',
        required=True,
        help='Formato 24 horas (ej: 22.0 = 22:00)'
    )
    
    activo = fields.Boolean(
        string='Activo',
        default=True
    )
    
    name = fields.Char(
        string='Descripción',
        compute='_compute_name',
        store=True
    )

    @api.depends('dia_semana', 'hora_inicio', 'hora_fin')
    def _compute_name(self):
        dias = dict(self._fields['dia_semana'].selection)
        for horario in self:
            if horario.dia_semana:
                hora_ini = self._float_to_time(horario.hora_inicio)
                hora_fin = self._float_to_time(horario.hora_fin)
                horario.name = f"{dias[horario.dia_semana]}: {hora_ini} - {hora_fin}"
            else:
                horario.name = ''

    @api.constrains('hora_inicio', 'hora_fin')
    def _check_horas(self):
        for horario in self:
            if not (0 <= horario.hora_inicio < 24):
                raise ValidationError(_('Hora de inicio debe estar entre 0 y 23:59'))
            if not (0 <= horario.hora_fin <= 24):
                raise ValidationError(_('Hora de fin debe estar entre 0 y 24:00'))
            if horario.hora_fin <= horario.hora_inicio:
                raise ValidationError(_('Hora de fin debe ser mayor a hora de inicio'))

    @staticmethod
    def _float_to_time(float_time):
        """Convierte float a formato HH:MM"""
        horas = int(float_time)
        minutos = int((float_time - horas) * 60)
        return f"{horas:02d}:{minutos:02d}"