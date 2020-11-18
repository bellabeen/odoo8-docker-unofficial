import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
import time

import openerp
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.osv import fields, osv, expression
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp import models, fields, api

class accounting_recurring(models.Model):
    _inherit = 'account.subscription'

    branch_id = fields.Many2one('wtc.branch', string='Branch', required=True)
    division =  fields.Selection([('Unit','Unit'),('Sparepart','Sparepart'),('Umum','Umum'),('Finance','Finance')], string='Division', change_default=True, select=True, required=True)
 
class account_subscription_line(osv.osv):
    _inherit = "account.subscription.line"

    def move_create(self, cr, uid, ids, context=None):
            tocheck = {}
            all_moves = []
            obj_model = self.pool.get('account.model')
            for line in self.browse(cr, uid, ids, context=context):
                data = {
                    'date': line.date,
                    'branch_id': line.subscription_id.branch_id.id,
                    'division': line.subscription_id.division,
                }
                move_ids = obj_model.generate(cr, uid, [line.subscription_id.model_id.id], data, context)
                tocheck[line.subscription_id.id] = True
                self.write(cr, uid, [line.id], {'move_id':move_ids[0]})
                all_moves.extend(move_ids)
            if tocheck:
                self.pool.get('account.subscription').check(cr, uid, tocheck.keys(), context)
            return all_moves

class wtc_account_move(osv.osv):
    _inherit = 'account.move'

class account_model(osv.osv):
    _inherit = "account.model"
 
    def generate(self, cr, uid, ids, data=None, context=None):
        if data is None:
            data = {}
        move_ids = []
        entry = {}
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        pt_obj = self.pool.get('account.payment.term')
        period_obj = self.pool.get('account.period')
        subscription_obj = self.pool.get('account.subscription')
          
        if context is None:
            context = {}

        if data.get('date', False):
            context = dict(context)
            context.update({'date': data['date']}) 
        if data.get('branch_id', False):
            context = dict(context)
            context.update({'branch_id': data['branch_id']}) 
        if data.get('division', False):
            context = dict(context)
            context.update({'division': data['division']})    

        move_date = context.get('date', time.strftime('%Y-%m-%d'))
        move_date = datetime.strptime(move_date,"%Y-%m-%d")
        for model in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            ctx.update({'company_id': model.company_id.id})
            
            period_ids = period_obj.find(cr, uid, dt=context.get('date', False), context=ctx)
            period_id = period_ids and period_ids[0] or False
            ctx.update({'journal_id': model.journal_id.id,'period_id': period_id})
           
            try:
                entry['name'] = model.name%{'year': move_date.strftime('%Y'), 'month': move_date.strftime('%m'), 'date': move_date.strftime('%Y-%m')}
            except:
                raise osv.except_osv(_('Wrong Model!'), _('You have a wrong expression "%(...)s" in your model!'))
            move_id = account_move_obj.create(cr, uid, {
                'ref': entry['name'],
                'period_id': period_id,
                'journal_id': model.journal_id.id,
                'date': context.get('date',time.strftime('%Y-%m-%d'))
            })
            move_ids.append(move_id)
            for line in model.lines_id:
                print "line :", line
                analytic_account_id = False
                if line.analytic_account_id:
                    if not model.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal!'),_("You have to define an analytic journal on the '%s' journal!") % (model.journal_id.name,))
                    analytic_account_id = line.analytic_account_id.id
                val = {
                    'move_id': move_id,
                    'journal_id': model.journal_id.id,
                    'period_id': period_id,
                    'analytic_account_id': analytic_account_id,
                }

                date_maturity = context.get('date',time.strftime('%Y-%m-%d'))
                if line.date_maturity == 'partner':
                    if not line.partner_id:
                        raise osv.except_osv(_('Error!'), _("Maturity date of entry line generated by model line '%s' of model '%s' is based on partner payment term!" \
                                                                "\nPlease define partner on it!")%(line.name, model.name))

                    payment_term_id = False
                    if model.journal_id.type in ('purchase', 'purchase_refund') and line.partner_id.property_supplier_payment_term:
                        payment_term_id = line.partner_id.property_supplier_payment_term.id
                    elif line.partner_id.property_payment_term:
                        payment_term_id = line.partner_id.property_payment_term.id
                    if payment_term_id:
                        pterm_list = pt_obj.compute(cr, uid, payment_term_id, value=1, date_ref=date_maturity)
                        if pterm_list:
                            pterm_list = [l[0] for l in pterm_list]
                            pterm_list.sort()
                            date_maturity = pterm_list[-1]

                val.update({
                    'name': line.name,
                    'quantity': line.quantity,
                    'debit': line.debit,
                    'credit': line.credit,
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.partner_id.id,
                    'date': context.get('date', time.strftime('%Y-%m-%d')),
                    'date_maturity': date_maturity,
                    'branch_id': context.get('branch_id'),
                    'division': context.get('division'),
                })

                account_move_line_obj.create(cr, uid, val, context=ctx) 
                print ctx              
        return move_ids



 


      