from openerp import models, fields, api
import time
from datetime import datetime
import itertools
from lxml import etree
from openerp import models,fields, exceptions, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import netsvc
from openerp.osv import osv

class masterCluster(models.Model):
    _name = 'teds.listing.table.insentif'
    _description = 'Listing Table Insentif'

    @api.onchange('cluster')
    def cluster_on_change(self):
        if self.cluster:
            self.cluster = str(self.cluster).upper()

        to_upper = {
            'cluster':self.cluster,
        }
        return {'value' :to_upper}


    # name = fields.Many2one('hr.job')
    name = fields.Selection([
        ('SALES COUNTER','SALES COUNTER'),
        ('SALESMAN TETAP','SALESMAN TETAP'),
        ('SALESMAN PARTNER','SALESMAN PARTNER'),
        ('SALES PAYROLL','SALES PAYROLL'),
        ('SALESMAN KONTRAK','SALESMAN KONTRAK'),
        ('KOORDINATOR SALESMAN','KOORDINATOR SALESMAN'),
        ('SOH','SOH'),
        ])
    cluster = fields.Char('Cluster')
    total = fields.Integer('Total')
    cash = fields.Integer('Cash')
    credit = fields.Integer('Credit')
    mediator = fields.Integer('Mediator')
    type_insentif = fields.Selection([
        ('cash_credit','Cash & Credit'),
        ('unit_credit_ke','Unit Credit Ke'),
        ('reward','Reward'),
        ])
    point = fields.Integer('Point')
    nilai_per_unit = fields.Integer('Nilai/Unit')
    akumulasi = fields.Integer('Akumulasi')
    insentif = fields.Integer('Insentif')

