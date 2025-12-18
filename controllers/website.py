from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class ReservaWebsiteController(http.Controller):

    @http.route('/reserva/canchas', type='http', auth='public', website=True)
    def canchas_list(self, **kwargs):
        """Lista de canchas disponibles"""
        canchas = request.env['reserva.cancha'].sudo().search([
            ('activa', '=', True),
            ('disponible_web', '=', True)
        ])
        
        return request.render('reserva_canchas.website_canchas', {
            'canchas': canchas,
        })

    @http.route('/reserva/nueva', type='http', auth='user', website=True)
    def nueva_reserva(self, **kwargs):
        """Formulario de nueva reserva"""
        cancha_id = kwargs.get('cancha_id')
        
        canchas = request.env['reserva.cancha'].sudo().search([
            ('activa', '=', True),
            ('disponible_web', '=', True)
        ])
        
        values = {
            'canchas': canchas,
            'cancha_id': int(cancha_id) if cancha_id else None,
        }
        
        return request.render('reserva_canchas.website_nueva_reserva', values)

    @http.route('/reserva/crear', type='http', auth='user', website=True, methods=['POST'])
    def crear_reserva(self, **post):
        """Crear nueva reserva desde web"""
        try:
            # Validar datos
            cancha_id = int(post.get('cancha_id'))
            fecha_inicio = post.get('fecha_inicio')
            fecha_fin = post.get('fecha_fin')
            
            if not all([cancha_id, fecha_inicio, fecha_fin]):
                raise ValidationError(_('Faltan datos obligatorios'))
            
            # Convertir fechas
            fecha_inicio_dt = fields.Datetime.from_string(fecha_inicio.replace('T', ' '))
            fecha_fin_dt = fields.Datetime.from_string(fecha_fin.replace('T', ' '))
            
            # Crear reserva
            reserva = request.env['reserva.reserva'].sudo().create({
                'partner_id': request.env.user.partner_id.id,
                'cancha_id': cancha_id,
                'fecha_inicio': fecha_inicio_dt,
                'fecha_fin': fecha_fin_dt,
                'numero_jugadores': int(post.get('numero_jugadores', 0)) or False,
                'notas': post.get('notas', ''),
                'state': 'pendiente',
            })
            
            return request.redirect('/my/reservas?mensaje=exito')
            
        except ValidationError as e:
            return request.redirect('/reserva/nueva?error=%s' % e.args[0])
        except Exception as e:
            return request.redirect('/reserva/nueva?error=Error al crear la reserva')

    @http.route('/reserva/disponibilidad', type='json', auth='public')
    def check_disponibilidad(self, cancha_id, fecha_inicio, fecha_fin):
        """Verificar disponibilidad de una cancha"""
        try:
            cancha = request.env['reserva.cancha'].sudo().browse(int(cancha_id))
            
            if not cancha.exists():
                return {'error': 'Cancha no encontrada'}
            
            # Buscar reservas conflictivas
            fecha_inicio_dt = fields.Datetime.from_string(fecha_inicio)
            fecha_fin_dt = fields.Datetime.from_string(fecha_fin)
            
            conflictos = request.env['reserva.reserva'].sudo().search([
                ('cancha_id', '=', cancha.id),
                ('state', 'not in', ['cancelada', 'no_show']),
                '|',
                    '&',
                        ('fecha_inicio', '<=', fecha_inicio_dt),
                        ('fecha_fin', '>', fecha_inicio_dt),
                    '&',
                        ('fecha_inicio', '<', fecha_fin_dt),
                        ('fecha_fin', '>=', fecha_fin_dt),
            ])
            
            return {
                'disponible': len(conflictos) == 0,
                'conflictos': len(conflictos),
                'precio_hora': cancha.precio_hora,
            }
            
        except Exception as e:
            return {'error': str(e)}