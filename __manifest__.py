{
    'name': 'Reserva de Canchas Deportivas',
    'version': '18.0.1.0.0',
    'category': 'Services/Bookings',
    'summary': 'Sistema completo de reservación de canchas deportivas',
    'description': """
        Módulo de Reservación de Canchas Deportivas
        ============================================
        * Gestión de canchas y horarios
        * Reservas con validaciones avanzadas
        * Portal web para usuarios externos
        * Tres roles: Admin, Staff y Usuario
        * Integración con website
        * Sistema de pagos y confirmaciones
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'website',
        'portal',
        'payment',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/cron.xml',
        'views/cancha_views.xml',
        'views/reserva_views.xml',
        'views/horario_views.xml',
        'views/menu_views.xml',
        'views/portal_templates.xml',
        'views/website_templates.xml',
        'report/reserva_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'reserva_canchas/static/src/css/backend.css',
            'reserva_canchas/static/src/js/reserva_calendar.js',
        ],
        'web.assets_frontend': [
            'reserva_canchas/static/src/css/frontend.css',
            'reserva_canchas/static/src/js/booking.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}