from openerp.osv import osv, fields
from datetime import datetime
import time 
import operator
from openerp.tools.translate import _
from openerp.tools import float_compare

class wtc_account_move(osv.osv):
    _inherit = 'account.move'
        
    _columns = {
                'cancel_uid' : fields.many2one('res.users',string="Cancelled by"),
                'confirm_uid' : fields.many2one('res.users',string="Posted by"),
                'cancel_date' : fields.datetime('Cancelled on'),
                'confirm_date' : fields.datetime('Posted on'),
                }
                
#    def post(self, cr, uid, ids, context=None):
#        obj_sequence = self.pool.get('ir.sequence')
#        res = super(wtc_account_move, self).post(cr, uid, ids, context=context)
#        seq_no = False
#        for move in self.browse(cr, uid, ids, context=context):
#            seq_no = obj_sequence.get_per_branch(cr, uid, voucher.branch_id.id, voucher.journal_id.code)
#            if move.journal_id.sequence_id:
#                seq_no = obj_sequence.get_per_branch(cr, uid, move.journal_id.branch_id.id, context=context)
#            if seq_no:x
#                self.write(cr, uid, [move.id], {'name':new_name})
#        return res

    def validate(self, cr, uid, ids, context=None):
        valid_moves = super(wtc_account_move, self).validate(cr, uid, ids, context=context)  
        if context == None :
            ctx = {}
        else :
            ctx = context.copy()
        ctx['novalidate'] = True
        branch_pool = self.pool.get('wtc.branch')             
        move_line = self.pool.get('account.move.line')  
        if not valid_moves :
            return valid_moves
        prec = self.pool['decimal.precision'].precision_get(cr, uid, 'Account')
        
        for move_id in valid_moves :
            branch_rekap = {}    
            move_lines = move_line.search(cr,uid,[
                                                 ('move_id','=',move_id)
                                                 ])
            line_ids = []
            if move_lines :
                move_lines = move_line.browse(cr,uid,move_lines)
            
                for x in move_lines :
                    if not x.branch_id :
                        continue
                    if x.branch_id not in branch_rekap :
                        branch_rekap[x.branch_id] = {}
                        branch_rekap[x.branch_id]['debit'] = x.debit
                        branch_rekap[x.branch_id]['credit'] = x.credit
                        branch_rekap[x.branch_id]['division'] = x.division
                        branch_rekap[x.branch_id]['total'] = x.debit + x.credit
                    else :
                        branch_rekap[x.branch_id]['debit'] += x.debit
                        branch_rekap[x.branch_id]['credit'] += x.credit
                        branch_rekap[x.branch_id]['total'] += x.debit + x.credit
                
                make_interco = False
                if len(branch_rekap.keys()) < 2 :
                    continue
                for key, values in branch_rekap.items() :
                    if values['debit'] != values['credit'] :
                        make_interco = True
                
                if not make_interco :
                    continue
                    
                moves = self.browse(cr,uid,[move_id])
                
                sorted_branch_rekap = dict(sorted(branch_rekap.items(), key=lambda x: x[1]['total'], reverse = True))
                first_branch_id = sorted_branch_rekap.keys()[0]
                inter_branch_header_account_id = sorted_branch_rekap.keys()[0].inter_company_account_id.id
                if not inter_branch_header_account_id :
                    raise osv.except_osv(('Perhatian !'), ("Account Inter belum diisi dalam Master branch %s!")%(sorted_branch_rekap.keys()[0].name))
                
                
                for key,value in sorted_branch_rekap.items() :
                    if key == first_branch_id :
                        continue
                    inter_branch_detail_account_id = key.inter_company_account_id.id                
                    if not inter_branch_detail_account_id :
                        raise osv.except_osv(('Perhatian !'), ("Account Inter belum diisi dalam Master branch %s - %s!")%(key.code, key.name))
                    
                    balance = value['debit']-value['credit']
                    debit = abs(balance) if balance < 0 else 0
                    credit = balance if balance > 0 else 0
    
                    if value['debit'] == value['credit'] :
                        continue
                    
                    move_line_create = {
                        'name': 'Interco %s'%(key.name),
                        'ref':'Interco %s'%(key.name),
                        'account_id': inter_branch_header_account_id,
                        'move_id': move_id,
                        'journal_id': moves.journal_id.id,
                        'period_id': moves.period_id.id,
                        'date': moves.date,
                        'debit': debit,
                        'credit': credit,
                        'branch_id' : key.id,
                        'division' : value['division'],
                    }
                    move_line2_create = {
                        'name': 'Interco %s'%(first_branch_id.name),
                        'ref':'Interco %s'%(first_branch_id.name),
                        'account_id': inter_branch_detail_account_id,
                        'move_id': move_id,
                        'journal_id': moves.journal_id.id,
                        'period_id': moves.period_id.id,
                        'date': moves.date,
                        'debit': credit,
                        'credit': debit,
                        'branch_id' : first_branch_id.id,
                        'division' : value['division'],
                    }
    
                    line_ids.append(move_line_create)
                    line_ids.append(move_line2_create)
            if len(line_ids) > 0 :            
                for line in line_ids :
                    self.pool.get('account.move.line').create(cr, uid, line, context=ctx)
        return valid_moves

    def post(self, cr, uid, ids, context=None):
        res = super(wtc_account_move, self).post(cr, uid, ids, context=context)
        cr.execute('UPDATE account_move '\
                   'SET confirm_uid=%s,confirm_date=%s '\
                   'WHERE id IN %s AND state=%s',
                   (uid,time.strftime('%Y-%m-%d %H:%M:%S'),tuple(ids),'posted'))
        return res
    
    def button_validate(self, cursor, user, ids, context=None):
        #self.write(cursor,user,ids,{'confirm_uid':user,'confirm_date':datetime.now()})        
        cursor.execute("""
            UPDATE account_move_line aml
            SET date_maturity = '%s'
            FROM account_account aa
            WHERE aml.account_id = aa.id
            AND aa.type in ('receivable', 'payable')
            AND aml.date_maturity IS NULL
            AND aml.move_id in %s
            """ % (self.pool.get('wtc.branch').get_default_date(cursor, user, ids), str(tuple(ids)).replace(',)',')')))
        vals = super(wtc_account_move,self).button_validate(cursor,user,ids,context=context)
        #for move in self.browse(cursor, user, ids, context=context):
        #    for line in move.line_id:
        #        if line.account_id.type in ['receivable','payable'] and not line.date_maturity :
        #            line.date_maturity =  datetime.now()
        return vals

    def button_cancel(self, cr, uid, ids, context=None):  
        vals = super(wtc_account_move,self).button_cancel(cr,uid,ids,context=context)
        ctx = context.copy()
        ctx['novalidate'] = True
        self.write(cr,uid,ids,{'cancel_uid':uid,'cancel_date':datetime.now()}, context=ctx)
        return vals          

