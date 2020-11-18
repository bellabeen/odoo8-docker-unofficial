import time
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp import tools, api
from select import select

class wtc_ir_sequence(osv.osv):
    _inherit = 'ir.sequence'

    def get_nik_per_branch(self, cr, uid, branch_id, context=None):
        doc_code = self.pool.get('wtc.branch').browse(cr, uid, branch_id).doc_code
        seq_name = '{0}{1}'.format('EMP', doc_code)

        ids = self.search(cr, uid, [('name','=',seq_name)])
        if not ids:
            prefix = '%(y)s%(month)s'
            prefix = doc_code + prefix
            ids = self.create(cr, SUPERUSER_ID, {'name':seq_name,
                                 'implementation':'standard',
                                 'prefix':prefix,
                                 'padding':3})

        return self.get_id(cr, uid, ids)

    def get_per_branch_date(self, cr, uid, branch_id, prefix, context=None):
        doc_code = self.pool.get('wtc.branch').browse(cr, uid, branch_id).doc_code
        seq_name = '{0}/{1}'.format(prefix, doc_code)

        ids = self.search(cr, uid, [('name','=',seq_name)])
        if not ids:
            prefix = '/%(y)s/%(month)s/%(day)s/'
            prefix = seq_name + prefix
            ids = self.create(cr, SUPERUSER_ID, {'name':seq_name,
                                 'implementation':'standard',
                                 'prefix':prefix,
                                 'padding':5})

        return self.get_id(cr, uid, ids)

    def get_per_branch(self, cr, uid, branch_id, prefix, context=None):
        doc_code = self.pool.get('wtc.branch').browse(cr, uid, branch_id).doc_code
        seq_name = '{0}/{1}'.format(prefix, doc_code)

        ids = self.search(cr, uid, [('name','=',seq_name)])
        if not ids:
            prefix = '/%(y)s/%(month)s/'
            prefix = seq_name + prefix
            ids = self.create(cr, SUPERUSER_ID, {'name':seq_name,
                                 'implementation':'standard',
                                 'prefix':prefix,
                                 'padding':5})

        return self.get_id(cr, uid, ids)

    def get_sequence(self, cr, uid, first_prefix, context=None):
        ids = self.search(cr, uid, [('name','=',first_prefix)])
        if not ids:
            prefix = first_prefix + '/%(y)s/%(month)s/'
            ids = self.create(cr, SUPERUSER_ID, {'name': first_prefix,
                                 'implementation': 'standard',
                                 'prefix': prefix,
                                 'padding': 5})
            
        return self.get_id(cr, uid, ids)
    
    def get_sequence_asset_category(self, cr, uid, first_prefix, context=None):
        ids = self.search(cr, uid, [('name','=','Asset_'+first_prefix)])
        if ids :
            ids = self.browse(cr,uid,ids).id
        if not ids:
            prefix = first_prefix
            suffix = '%(month)s%(y)s'
            ids = self.create(cr, SUPERUSER_ID, {'name': 'Asset_'+first_prefix,
                                 'implementation': 'standard',
                                 'prefix': prefix,
                                 'suffix':suffix,
                                 'padding': 5})        
        return ids

    def get_sequence_no_kwitansi(self, cr, uid, first_prefix, context=None):
        seq_name = first_prefix

        ids = self.search(cr, uid, [('name','=',seq_name)])
        if not ids:
            prefix = seq_name
            suffix = '%(y)s'
            prefix = seq_name + suffix
            ids = self.create(cr, SUPERUSER_ID, {'name':seq_name,
                                 'implementation':'standard',
                                 'prefix':prefix,
                                 'padding':5})

        return self.get_id(cr, uid, ids)
