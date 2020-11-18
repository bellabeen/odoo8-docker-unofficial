# -*- coding: utf-8 -*-
from openerp import http

# class TedsApiRestful(http.Controller):
#     @http.route('/teds_api_restful/teds_api_restful/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/teds_api_restful/teds_api_restful/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('teds_api_restful.listing', {
#             'root': '/teds_api_restful/teds_api_restful',
#             'objects': http.request.env['teds_api_restful.teds_api_restful'].search([]),
#         })

#     @http.route('/teds_api_restful/teds_api_restful/objects/<model("teds_api_restful.teds_api_restful"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('teds_api_restful.object', {
#             'object': obj
#         })