from openerp.osv import osv,fields
import time
from openerp import workflow

class wtc_start_stop_wo(osv.osv):
    _name = 'wtc.start.stop.wo'
    
    def _get_work_order_id(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('work_order_id', False)
    
    def _get_mekanik_id(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('mekanik_id', False)
    
    _columns = {
                'work_order_id':fields.many2one('wtc.work.order', 'Work Order', domain="[('mekanik_id','in',[mekanik_id,False]), ('state','in',['open','approved'])]"),
                'mekanik_id':fields.many2one('res.users', 'Mekanik'),
                'employee_id':fields.many2one('hr.employee','Employee'),
                'start':fields.datetime('Start', readonly=True),
                'date_break':fields.datetime('Break', readonly=True),
                'end_break':fields.datetime('End Break', readonly=True),
                'finish':fields.datetime('Finish', readonly=True),
                }
    _defaults = {
        'work_order_id': _get_work_order_id,        
        'mekanik_id': _get_mekanik_id,
    }
    
    def btn_start(self, cr, uid, ids, context=None):
        tgl_start = time.strftime('%Y-%m-%d %H:%M:%S')
        a = self.browse(cr,uid,ids)
        obj_wo_a = self.pool.get('wtc.work.order')
        obj_id_a = obj_wo_a.search(cr,uid,[('id','=',a.work_order_id.id)])
        obj_strt = obj_wo_a.browse(cr,uid,obj_id_a)
        inv = self.browse(cr, uid, ids[0], context=context)
        
        if obj_strt :
            obj_wo_a.write(cr, uid, obj_id_a, {'state_wo':'in_progress','start':tgl_start,'mekanik_id':inv.mekanik_id.id}, context=context)
            self.write(cr, uid, ids, {'start':tgl_start,'date_break':a.work_order_id.date_break,'end_break':a.work_order_id.end_break,'finish':a.work_order_id.finish}, context=context)
            workflow.trg_validate(uid, 'wtc.work.order', obj_strt.id, 'start_wo', cr) 
        return True
    
    def btn_break(self, cr, uid, ids, context=None):
        tgl_break = time.strftime('%Y-%m-%d %H:%M:%S')
        b = self.browse(cr,uid,ids)
        obj_wo_b = self.pool.get('wtc.work.order')
        obj_id_b = obj_wo_b.search(cr,uid,[('id','=',b.work_order_id.id)])
        obj_brk = obj_wo_b.browse(cr,uid,obj_id_b)
        cek_finish = b.work_order_id.finish
        
        if obj_brk and not cek_finish :
            obj_wo_b.write(cr, uid, obj_id_b, {'state_wo':'break','date_break':tgl_break}, context=context)
            self.write(cr, uid, ids, {'date_break':tgl_break,'start':b.work_order_id.start,'end_break':b.work_order_id.end_break,'finish':b.work_order_id.finish}, context=context)
            workflow.trg_validate(uid, 'wtc.work.order', obj_brk.id, 'break_wo', cr) 
        return True
    
    def btn_end_break(self, cr, uid, ids, context=None):
        tgl_end_break = time.strftime('%Y-%m-%d %H:%M:%S')
        c = self.browse(cr,uid,ids)
        obj_wo_c = self.pool.get('wtc.work.order')
        obj_id_c = obj_wo_c.search(cr,uid,[('id','=',c.work_order_id.id)])
        obj_ebrk = obj_wo_c.browse(cr,uid,obj_id_c)
        cek_finish2 = c.work_order_id.finish
         
        if obj_ebrk and not cek_finish2 :
            obj_wo_c.write(cr, uid, obj_id_c, {'state_wo':'in_progress','end_break':tgl_end_break}, context=context)
            self.write(cr, uid, ids, {'end_break':tgl_end_break,'start':c.work_order_id.start,'date_break':c.work_order_id.date_break,'finish':c.work_order_id.finish}, context=context)
            workflow.trg_validate(uid, 'wtc.work.order', obj_ebrk.id, 'start_wo', cr) 
        return True
    
    def btn_finish(self, cr, uid, ids, context=None):
        tgl_finish = time.strftime('%Y-%m-%d %H:%M:%S')
        d = self.browse(cr,uid,ids)
        obj_wo_d = self.pool.get('wtc.work.order')
        obj_id_d = obj_wo_d.search(cr,uid,[('id','=',d.work_order_id.id)])
        obj_fns = obj_wo_d.browse(cr,uid,obj_id_d)
        
        if obj_fns :
            obj_wo_d.write(cr, uid, obj_id_d, {'state_wo':'finish','finish':tgl_finish}, context=context)
            self.write(cr, uid, ids, {'finish':tgl_finish,'start':d.work_order_id.start,'date_break':d.work_order_id.date_break,'end_break':d.work_order_id.end_break}, context=context)
            workflow.trg_validate(uid, 'wtc.work.order', obj_fns.id, 'end_wo', cr) 
        return True
    
    def onchange_wo(self, cr, uid, ids, work_order_id):
        v = {}
        if work_order_id :
            s=self.pool.get("wtc.work.order").browse(cr, uid, work_order_id)
            v['start']=s.start
            v['date_break']=s.date_break
            v['end_break']=s.end_break
            v['finish']=s.finish
        else :
            v['start']=False
            v['date_break']=False
            v['end_break']=False
            v['finish']=False
        
        return {'value':v}
    
    
    def mekanik_id_change(self,cr,uid,ids,mekanik_id):
        if mekanik_id :
            obj_employee=self.pool.get('hr.employee')
            obj_search_empl=obj_employee.search(cr, uid,[('user_id','=',mekanik_id)])
            obj_browse_empl=obj_employee.browse(cr,uid,obj_search_empl)
            return {'value' : {'employee_id':obj_browse_empl.id}}
    
class wtc_start_stop_wo(osv.osv):
    _inherit="wtc.work.order"
    _columns={
              'state_wo': fields.selection([('in_progress','In Progress'),('break','Break'),('finish','Finish')], 'State', readonly=True),
              }
    
    