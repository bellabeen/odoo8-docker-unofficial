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
            'status':status
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
    _logger.error("Token is expired or invalid!")    
    return invalid_response(401, 'invalid_token', "Token is expired or invalid!",method)

def check_valid_token(func):
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        access_token = request.httprequest.headers.get('access_token')
        method = request.httprequest.method
        if not access_token:
            info = "Missing access token in request header!"
            error = 'access_token_not_found'
            _logger.error(info)
            return invalid_response(400, error, info,method)

        access_token_data = request.env['oauth.access_token'].sudo().search(
            [('token', '=', access_token)], order='id DESC', limit=1)

        if access_token_data._get_access_token(user_id=access_token_data.user_id.id) != access_token:
            return invalid_token(method)

        request.session.uid = access_token_data.user_id.id
        request.uid = access_token_data.user_id.id
        return func(self, *args, **kwargs)

    return wrap

class ControllerREST(http.Controller):
    @http.route('/api/enginereport/penjualan_md', methods=['POST'], type='json', auth='none', csrf=False)
    @check_valid_token
    def penjualan_md(self,**post):           
        log_format = '%(asctime)s: %(message)s'
        logging.basicConfig(format=log_format, level=logging.INFO, datefmt='%H:%M:%S')

        penjualan_md = request.env['wtc.report.penjualan.md.wizard']
        query = penjualan_md._query_penjualan_md(
            division = post['division'] if 'division' in post and post['division'] else None,
            product_ids = post['product_ids'] if 'product_ids' in post and post['product_ids'] else None,
            start_date = post['start_date'] if 'start_date' in post and post['start_date'] else None,
            end_date = post['end_date'] if 'end_date' in post and post['end_date'] else None,
            state = post['state'] if 'state' in post and post['state'] else None,
            branch_ids = post['branch_ids'] if 'branch_ids' in post and post['branch_ids'] else None,
            dealer_ids = post['dealer_ids'] if 'dealer_ids' in post and post['dealer_ids'] else None,  
            tz = '7 hours'
        )
        
        request.env.cr.execute(query)
        results = request.env.cr.dictfetchall()        
        
        for result in results:
            if result['soc_id'] > 0:
                result.update({
                    'qty': -result['qty'],
                    'hpp': -result['hpp'],
                    'harga_jual': -result['harga_jual'],
                    'disc': -result['disc'],
                    'harga_jual_excl_tax': -result['harga_jual_excl_tax'],
                    'total_hpp': -result['total_hpp'],
                    'nett_sales': -result['nett_sales'],
                    'discount_cash_avg': -result['discount_cash_avg'],
                    'discount_lain_avg': -result['discount_lain_avg'],
                    'discount_program_avg': -result['discount_program_avg'],
                    'dpp': -result['dpp'],
                    'tax': -result['tax'],
                    'total': -result['total'],
                    'gp': -result['gp'],
                    'gp_avg': -result['gp_avg'],
                })

        return {
            "status":1,
            "data": results
        }
