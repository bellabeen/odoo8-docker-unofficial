from openerp.osv import fields, osv

class wtc_branch_config(osv.osv):
    _inherit = 'wtc.branch.config'
    _columns = {
                
        'wo_kpb_journal_id': fields.many2one('account.journal','Journal WO KPB', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Work Order untuk type KPB",),
        'wo_claim_journal_id': fields.many2one('account.journal','Journal WO Claim', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Work Order untuk Claim ",),   
        'wo_reg_journal_id': fields.many2one('account.journal','Journal WO Regular dan Part Sales', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Work Order untuk type Reguler dan Part Sales ",),
        
        'wo_war_journal_id': fields.many2one('account.journal','Journal WO Job Return', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Work Order untuk type Job Return ",), 
                
        'wo_collecting_kpb_journal_id': fields.many2one('account.journal','Journal Collecting Piutang KPB', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Collecting piutang kpb  ",),
        'wo_collecting_claim_journal_id': fields.many2one('account.journal','Journal Collecting Piutang Claim', 
                                        help="Field ini digunakan untuk setting account journal. "
                                       "pada transaksi Collecting piutang claim",),          
  
    }