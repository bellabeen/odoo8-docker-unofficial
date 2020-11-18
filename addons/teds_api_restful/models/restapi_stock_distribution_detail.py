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
    @http.route('/api/enginereport/stock_distribution_detail', method=['POST'], type='json', auth='none', csrf=False)
    @check_valid_token
    def stock_distribution_detail(self, **post):
        log_format = '%(asctime)s: %(message)s'
        logging.basicConfig(format=log_format, level=logging.INFO, datefmt='%H:%M:%S')
                      
        today = datetime.now().date()
        last_day_of_month = calendar.monthrange(today.year, today.month)
        start_date = post['start_date'] if 'start_date' in post else today.replace(day=1)
        end_date = post['end_date'] if 'end_date' in post else today.replace(day=last_day_of_month[1])
        state = post['state'] if 'state' in post else 'all'
        division = post['division'] if 'division' in post else None
        trx_type = post['trx_type'] if 'trx_type' in post else None
        branch_ids = post['branch_ids'] if 'branch_ids' in post else [40]
        dealer_ids = post['dealer_ids'] if 'dealer_ids' in post else None
        state_str = ''
        division_str = 'All'
        trx_type_str = 'All'

        rsp = request.env['wtc.report.stock.distribution']
        query = rsp._query_report_stock_distribution_detail(
            state=state,
            division=division,
            trx_type=trx_type,
            start_date=start_date,
            end_date=end_date,
            branch_ids=branch_ids,
            dealer_ids=dealer_ids,
            state_str=state_str,
            division_str=division_str,
            trx_type_str=trx_type_str
        )

        request.cr.execute(query)
        ress = request.cr.dictfetchall()

        return {
            'status': 1,
            'data': ress
        }