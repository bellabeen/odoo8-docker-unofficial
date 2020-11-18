import functools
import openerp
import yaml
import logging
import calendar
import werkzeug.wrappers
from openerp import http
from datetime import datetime, timedelta, date
from openerp.http import request, Response
from openerp.exceptions import AccessDenied, AccessError, ValidationError
try:
    import simplejson as json
except ImportError:
    import json

_logger = logging.getLogger(__name__)

def invalid_response(status, error, info, method):
    if method == 'POST':
        return {
            'error': error,
            'error_descrip': info,
            'status': status
        }
    elif method == 'GET':
        return werkzeug.wrappers.Response(
            status=status,
            content_type='application/json; charset=utf-8',
            response=json.dumps({
                'error': error,
                'error_descrip': info,
            }),
        )

def invalid_token(method):
    _logger.error('Token is expired or invalid!')
    return invalid_response(401, 'invalid_token', 'Token is expired or invalid', method)

def check_valid_token(func):
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        access_token = request.httprequest.headers.get('access_token')
        method = request.httprequest.method
        if not access_token:
            info = 'Missing access token in request header!'
            error = 'access_token_not_found'
            _logger.error(info)
            return invalid_response(400, error, info, method)
        access_token_data = request.env['oauth.access_token'].sudo().search(
            [('token', '=', access_token)],
            order='id DESC',
            limit=1
        )
        
        if access_token_data._get_access_token(user_id=access_token_data.user_id.id) != access_token:
            return invalid_token(method)

        request.session.uid = access_token_data.user_id.id
        request_uid = access_token_data.user_id.id
        return func(self, *args, **kwargs)
    
    return wrap

class ControllerREST(http.Controller):
    @http.route('/api/enginereport/stock_sparepart', method=['POST'], type='json', auth='none', csrf=False)
    @check_valid_token
    def stock_sparepart(self, **post):
        log_format = '%(asctime)s: %(message)s'
        logging.basicConfig(format=log_format, level=logging.INFO, datefmt='%H:%M:%S')
                      
        location_status = post['location_status'] if 'location_status' in post and post['location_status'] else 'all'
        product_ids = post['product_ids'] if 'product_ids' in post and post['product_ids'] else None
        branch_ids = post['branch_ids'] if 'branch_ids' in post and post['branch_ids'] else None 
        location_ids = post['location_ids'] if 'location_ids' in post and post['location_ids'] else None
        
        rspw = request.env['wtc.report.stock.sparepart.wizard']
        query = rspw._query_stock_sparepart(
            location_status = location_status,
            product_ids = product_ids,
            branch_ids = branch_ids,
            location_ids = location_ids
        )
        
        request.env.cr.execute(query)
        results = request.env.cr.dictfetchall()

        return {
            'status': 1,
            'data': results
        }