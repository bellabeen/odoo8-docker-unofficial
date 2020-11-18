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
    @http.route('/api/enginereport/mutasi_detail', method=['POST'], type='json', auth='none', csrf=False)
    @check_valid_token
    def mutasi_detail(self, **post):
        log_format = '%(asctime)s: %(message)s'
        logging.basicConfig(format=log_format, level=logging.INFO, datefmt='%H:%M:%S')

        today = datetime.now().date()
        last_day_of_month = calendar.monthrange(today.year, today.month)
        start_date = post['start_date'] if 'start_date' in post and post['start_date'] else today.replace(day=1)
        end_date = post['end_date'] if 'end_date' in post and post['end_date'] else today.replace(day=last_day_of_month[1])
        branch_ids = post['branch_ids'] if 'branch_ids' in post and post['branch_ids'] else [40]
        division = post['division'] if 'division' in post and post['division'] else None
        state = post['state'] if 'state' in post and post['state'] else None
        tz = '7 hours'
        
        query_where = ""
        query_saldo_where = ""
        if branch_ids :
            query_where += " and mo.branch_id in %s " % str(tuple(branch_ids)).replace(',)', ')') 

        if division:
            query_division = " and mo.division ='%s' " %(division)

        if state=='confirm':
            query_state = " and mo.state ='confirm' "
        elif state=='done':
            query_state = " and mo.state ='done' "
        else:
            query_state = " "

        query="""
            select b.code AS branch_code
            , b.name AS branch_name
            , mo.name AS mo_mutasi
            , mo.state AS mo_state
            , mo.confirm_date + interval '7 hours' AS confirm_date
            , b2.code AS branch_req_code
            , b2.name AS branch_req_name
            , p.name_template
            , pav.code AS pav_code
            , p.default_code
            , pt.description
            , case when mo.state = 'cancelled' then -1 * mol.qty else mol.qty end AS qty
            , (COALESCE((
                SELECT cost
                FROM product_price_history_branch pphb
                WHERE product_id = p.id
                AND warehouse_id = b.warehouse_id
                AND datetime + interval '7 hours' <= mo.confirm_date + interval '7 hours' 
                ORDER BY pphb.datetime DESC LIMIT 1),0)
            ) as hpp
            , mol.unit_price as het
            , mol.unit_price / 1.1 as harga_jual
            , pc.name as categ1
            , coalesce(pc2.name, '') as categ2
            , mo.division
            , mol.product_id
            , b.warehouse_id
            , mol.supply_qty
            , ((case when mo.state = 'cancelled' then -1 * mol.qty else mol.qty end)* COALESCE((
                SELECT cost
                FROM product_price_history_branch pphb
                WHERE product_id = p.id
                AND warehouse_id = b.warehouse_id
                AND datetime + interval '7 hours' <= mo.confirm_date + interval '7 hours' 
                ORDER BY pphb.datetime DESC LIMIT 1),0)
            ) as tot_hpp
            , ((case when mo.state = 'cancelled' then -1 * mol.qty else mol.qty end) * mol.unit_price / 1.1) as tot_hrg_jual
            from wtc_mutation_order mo
            inner join wtc_mutation_order_line mol on mol.order_id = mo.id
            inner join wtc_branch b on b.id = mo.branch_id
            left join wtc_branch b2 on b2.id = mo.branch_requester_id
            left join product_product p on p.id = mol.product_id 
            left join product_template pt on pt.id = p.product_tmpl_id
            left join product_category pc on pc.id = pt.categ_id
            left join product_category pc2 on pc2.id = pc.parent_id
            left join product_attribute_value_product_product_rel pavpp ON p.id = pavpp.prod_id 
            left join product_attribute_value pav ON pavpp.att_id = pav.id 
            where ((mo.state in ('done', 'confirm') and mo.date >= '%s' and mo.date <= '%s') 
            or (mo.state in ('cancelled') and mo.cancelled_date + interval '7 hours' >= '%s' and mo.cancelled_date + interval '7 hours' <= '%s'))
             %s %s %s
            """ % (start_date,end_date,start_date,end_date,query_division,query_where,query_state)
        
        request.env.cr.execute(query)
        results = request.env.cr.dictfetchall()

        return {
            'status': 1,
            'data': results
        }