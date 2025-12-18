from odoo import http, _, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ReservaPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'reserva_count' in counters:
            reserva_count = request.env['reserva.reserva'].search_count([
                ('partner_id', '=', request.env.user.partner_id.id)
            ]) if request.env['reserva.reserva'].check_access_rights('read', raise_exception=False) else 0
            values['reserva_count'] = reserva_count
        return values

    @http.route(['/my/reservas', '/my/reservas/page/<int:page>'], 
                type='http', auth='user', website=True)
    def portal_my_reservas(self, page=1, date_begin=None, date_end=None, 
                          sortby=None, filterby=None, **kw):
        """Portal de reservas del usuario"""
        Reserva = request.env['reserva.reserva']
        
        domain = [('partner_id', '=', request.env.user.partner_id.id)]
        
        # Filtros
        searchbar_filters = {
            'all': {'label': _('Todas'), 'domain': []},
            'activas': {'label': _('Activas'), 
                       'domain': [('state', 'in', ['borrador', 'pendiente', 'confirmada', 'en_curso'])]},
            'pasadas': {'label': _('Pasadas'), 
                       'domain': [('state', 'in', ['completada', 'cancelada', 'no_show'])]},
        }
        
        # Ordenamiento
        searchbar_sortings = {
            'date': {'label': _('Fecha'), 'order': 'fecha_inicio desc'},
            'name': {'label': _('Número'), 'order': 'name'},
            'state': {'label': _('Estado'), 'order': 'state'},
        }
        
        # Valores por defecto
        if not sortby:
            sortby = 'date'
        if not filterby:
            filterby = 'activas'
        
        order = searchbar_sortings[sortby]['order']
        domain += searchbar_filters[filterby]['domain']
        
        # Conteo
        reserva_count = Reserva.search_count(domain)
        
        # Paginación
        pager = portal_pager(
            url='/my/reservas',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=reserva_count,
            page=page,
            step=self._items_per_page
        )
        
        # Buscar reservas
        reservas = Reserva.search(domain, order=order, 
                                 limit=self._items_per_page, 
                                 offset=pager['offset'])
        
        values = {
            'reservas': reservas,
            'page_name': 'reserva',
            'pager': pager,
            'default_url': '/my/reservas',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        }
        
        return request.render('reserva_canchas.portal_my_reservas', values)

    @http.route(['/my/reservas/<int:reserva_id>'], 
                type='http', auth='user', website=True)
    def portal_reserva_detail(self, reserva_id, **kw):
        """Detalle de una reserva"""
        reserva = request.env['reserva.reserva'].browse(reserva_id)
        
        # Verificar acceso
        if reserva.partner_id.id != request.env.user.partner_id.id:
            return request.redirect('/my')
        
        values = {
            'reserva': reserva,
            'page_name': 'reserva',
        }
        
        return request.render('reserva_canchas.portal_reserva_detail', values)

    @http.route(['/my/reservas/<int:reserva_id>/cancelar'], 
                type='http', auth='user', website=True, methods=['POST'])
    def portal_reserva_cancelar(self, reserva_id, **post):
        """Cancelar una reserva desde el portal"""
        reserva = request.env['reserva.reserva'].sudo().browse(reserva_id)
        
        # Verificar acceso y permisos
        if reserva.partner_id.id != request.env.user.partner_id.id:
            return request.redirect('/my')
        
        if not reserva.puede_cancelar:
            return request.redirect('/my/reservas/%s?error=no_cancelable' % reserva_id)
        
        try:
            reserva.write({
                'state': 'cancelada',
                'fecha_cancelacion': fields.Datetime.now(),
                'motivo_cancelacion': post.get('motivo', 'Cancelado por el usuario desde el portal')
            })
            reserva.message_post(body=_('Reserva cancelada por el usuario'))
            
            return request.redirect('/my/reservas?mensaje=cancelada')
        except Exception as e:
            return request.redirect('/my/reservas/%s?error=%s' % (reserva_id, str(e)))