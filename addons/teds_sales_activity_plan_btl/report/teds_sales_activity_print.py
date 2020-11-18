import time
from openerp.osv import osv
from openerp.report import report_sxw
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning

class teds_act_plan_btl(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(teds_act_plan_btl, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'detail_ids': self._get_detail,
            'branch':self._get_branch,
            'periode':self._get_periode,
            'no_urut': self.no_urut,
            'total_biaya_tdm':self._get_total_biaya_tdm,
            'total_biaya_leasing':self._get_total_biaya_leasing,
            'total_biaya_tdm_ppn':self._get_total_biaya_tdm_ppn,
            'total_biaya_leasing_ppn':self._get_total_biaya_leasing_ppn,
            'create_uid':self._get_create_uid,
            'create_date':self._get_create_date,
        })

        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no

    def _get_branch(self,data):
        return data['branch_id']
    
    def _get_periode(self,data):
        return data['periode']


    def _get_detail(self,data):
        return data['detail_ids']

    def _get_total_biaya_leasing(self,data):
        return data['total_biaya_leasing']

    def _get_total_biaya_tdm(self,data):
        return data['total_biaya_tdm']
    
    def _get_total_biaya_leasing_ppn(self,data):
        return data['total_biaya_leasing_ppn']

    def _get_total_biaya_tdm_ppn(self,data):
        return data['total_biaya_tdm_ppn']

    def _get_create_uid(self,data):
        return data['create_uid']
    
    def _get_create_date(self,data):
        return data['create_date']

class act_plan_btl_print(osv.AbstractModel):
    _name = 'report.teds_sales_activity_plan_btl.teds_act_plan_btl_print'
    _inherit = 'report.abstract_report'
    _template = 'teds_sales_activity_plan_btl.teds_act_plan_btl_print'
    _wrapped_report_class = teds_act_plan_btl

class teds_act_plan_btl_tree(report_sxw.rml_parse):
    ress = False
    def __init__(self, cr, uid, name, context):
        super(teds_act_plan_btl_tree, self).__init__(cr, uid, name, context=context)
        
        act_ids = []
        ids = context.get('active_ids')
        lines = self.pool.get('teds.sales.plan.activity.line').browse(cr, uid, ids)
        res_uid = context.get('uid')
        user = self.pool.get('res.users').browse(cr, uid, res_uid).name
        detail_ids = []
        total_biaya_tdm = 0
        total_biaya_leasing = 0
        total_biaya_tdm_ppn = 0
        total_biaya_leasing_ppn = 0
        for line in lines:
            if line.activity_id.name not in act_ids:
                act_ids.append(line.activity_id.name)

            if line.total_biaya > 0 and line.state in ('confirmed','done'):
                biaya_ids = []
                history_ids = [] 
                detail_unit_ids = False
                
                if len(line.detail_biaya_ids) > 0:
                    for biaya in line.detail_biaya_ids:
                        if biaya.name == 'Leasing':
                            total_biaya_leasing += biaya.amount
                            total_biaya_leasing_ppn += biaya.subtotal
                        elif biaya.name == 'Dealer':
                            total_biaya_tdm += biaya.amount
                            total_biaya_tdm_ppn += biaya.subtotal

                        biaya_ids.append({
                            'name':biaya.name,
                            'finco':biaya.finco_id.name if biaya.finco_id != None else '',
                            'amount':biaya.amount,
                            'subtotal':biaya.subtotal,
                        })
                tot_history = len(line.history_location_ids)
                mulai = 0
                if tot_history > 0:
                    categ_list = {}
                    for history in line.history_location_ids:
                        mulai += 1
                        history_ids.append({
                            'name':history.name,
                            'qty':history.qty,
                        })

                        if mulai == tot_history:
                            for unit in history.detail_ids:
                                if not categ_list.get(unit.categ_id.name):
                                    categ_list[unit.categ_id.name] = {'categ_id':unit.categ_id.name,'qty':1}
                                else:
                                    categ_list[unit.categ_id.name]['qty'] += 1

                            detail_unit_ids = categ_list.values()

                detail_ids.append({
                    'name':line.name,
                    'alamat':line.street,
                    'rt':line.rt,
                    'rw':line.rw,
                    'kelurahan':line.kelurahan_id.name,
                    'kecamatan':line.kecamatan_id.name,
                    'city':line.city_id.name,
                    'start_date':line.start_date,
                    'end_date':line.end_date,
                    'pic':line.pic_id.name,
                    'nik':line.nik,
                    'jabatan':line.job,
                    'no_telp':line.no_telp,
                    'display_unit':line.display_unit,
                    'target_unit':line.target_unit,
                    'pencapaian_unit':sum([h.qty for h in line.history_location_ids]),
                    'biaya_ids':biaya_ids,
                    'history_ids':history_ids,
                    'detail_unit_ids':detail_unit_ids,
                    'jarak':line.titik_keramaian_id.jarak if line.titik_keramaian_id.jarak else '0' ,
                    'waktu':line.titik_keramaian_id.waktu if line.titik_keramaian_id.waktu else '0',
                    'foto':line.foto,
                })
        if len(act_ids) > 1:
            raise osv.except_osv(('Error !'), ('Activity Plan tidak boleh lebih dari satu ! \n %s'%str(act_ids))) 

   
        self.ress = {
            'user': user,
            'branch': str(line.branch_id.name),
            'periode': str(line.activity_id.name_get().pop()[1]),
            'total_biaya_tdm':total_biaya_tdm,
            'total_biaya_leasing':total_biaya_leasing,
            'total_biaya_tdm_ppn':total_biaya_tdm_ppn,
            'total_biaya_leasing_ppn':total_biaya_leasing_ppn,
            'detail_ids': detail_ids,
            'create_uid':line.create_uid.name,
            'create_date':line.create_date,
        }
        self.localcontext.update({
            'detail_ids': self.detail_ids,
            'branch':self.branch,
            'periode':self.periode,
            'no_urut': self.no_urut,
            'total_biaya_tdm':self.total_biaya_tdm,
            'total_biaya_leasing':self.total_biaya_leasing,
            'total_biaya_tdm_ppn':self.total_biaya_tdm_ppn,
            'total_biaya_leasing_ppn':self.total_biaya_leasing_ppn,
            'create_uid':self.create_uid,
            'create_date':self.create_date,
        })
        self.no = 0
    def no_urut(self):
        self.no+=1
        return self.no

    def branch(self):
        return self.ress['branch']
    def periode(self):
        return self.ress['periode']
    def detail_ids(self):
        return self.ress['detail_ids']
    def total_biaya_tdm(self):
        return self.ress['total_biaya_tdm']
    def total_biaya_leasing(self):
        return self.ress['total_biaya_leasing']
    def total_biaya_tdm_ppn(self):
        return self.ress['total_biaya_tdm_ppn']
    def total_biaya_leasing_ppn(self):
        return self.ress['total_biaya_leasing_ppn']
    def create_uid(self):
        return self.ress['create_uid']
    def create_date(self):
        return self.ress['create_date']


class act_plan_btl_print_tree(osv.AbstractModel):
    _name = 'report.teds_sales_activity_plan_btl.teds_act_plan_btl_print_tree'
    _inherit = 'report.abstract_report'
    _template = 'teds_sales_activity_plan_btl.teds_act_plan_btl_print_tree'
    _wrapped_report_class = teds_act_plan_btl_tree



