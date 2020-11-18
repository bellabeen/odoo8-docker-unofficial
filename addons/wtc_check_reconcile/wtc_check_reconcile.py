from openerp.osv import fields,osv


class wtc_check_reconcile(osv.osv):
    _name="wtc.check.reconcile"
    _columns={
              'move_line_id':fields.many2one('account.move.line','Reconcile'),
              "branch_id":fields.many2one("wtc.branch",'Branch' ),
              'account_id':fields.many2one('account.account','Account',domain="[('reconcile','=',True)]"),
              'check_reconcile_line':fields.one2many('wtc.check.reconcile.line','check_reconcile_id','Check Reconcile Lines')
              }
    
    def onchange_branch_id_account_id(self,cr,uid,ids,branch_id,account_id):
#         print '#############',branch_id 
        value={}
        dom={}
        
        value['move_line_id']=False
        value['wtc_check_reconcile_line']=False
#         dom['move_line_id'] = [(1, '=', 0)]
        if branch_id and account_id:
            dom['move_line_id'] = [
                                   ('branch_id', '=', branch_id),
                                   ('account_id','=',account_id),
                                    ]
        else:
            dom['move_line_id']=[('id','=',0)]
            
        return {'value':value,'domain':dom}
#         print 'aaaaaaaaaaaaaaa',dom
    
    def onchange_move_line(self,cr,uid,ids,move_line_id):
        value={}
        move_line_list=[]
        
        aml=self.pool.get('account.move.line').browse(cr,uid,move_line_id)
        reconcile_id=aml.reconcile_id.id if aml.reconcile_id else False
        if not reconcile_id:
            reconcile_id=aml.reconcile_partial_id.id if aml.reconcile_partial_id else False

        if reconcile_id :
            query="""
                select *
                from account_move_line 
                where reconcile_id=%s
                or reconcile_partial_id=%s 
                """ %(reconcile_id,reconcile_id)
                      
            cr.execute(query)    
            ress = cr.dictfetchall()

            for res in ress :
                move_line_list.append([0,0,{
                    'name':res['name'],
                    'journal':res['journal_id'],
                    'ref':res['reconcile_ref'],
                    'date':res['create_date'],
                    'partner':res['partner_id'],
                    'debit':res['debit'],
                    'credit':res['credit']
                }])

            value['check_reconcile_line'] = move_line_list
        else:
            value['check_reconcile_line'] = False
        return {'value':value}
        
            
#         print 'AAAAAAAAA',check_pool
        
        
        
        
class wtc_check_reconcile_line(osv.osv):
    _name='wtc.check.reconcile.line'
    _columns={
              'check_reconcile_id':fields.many2one('wtc.check.reconcile'),
              'name':fields.char('Name'),
              'journal':fields.many2one('account.journal','Journal'),
              'ref':fields.char('Reference'),
              'date':fields.date('Effective Date'),
              'partner':fields.char('Partner'),
              'debit':fields.char('Debit'),
              'credit':fields.char('Credit'),
              }
    
    