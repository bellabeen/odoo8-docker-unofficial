import itertools
import tempfile
from cStringIO import StringIO
import base64
import csv
import codecs
from openerp.osv import orm, fields
from openerp.tools.translate import _


class AccountCSVExport(orm.TransientModel):
    _inherit = "teds.generate.invoice"

    wbf = {}

        

    # def _get_header_account(self, cr, uid, ids, context=None):
    #     return [_(u'CODE'),
    #             _(u'NAME'),
    #             _(u'DEBIT'),
    #             _(u'CREDIT'),
    #             _(u'BALANCE'),
    #             ]
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_qty, line.product_id)
            res[line.id]=taxes['total']
        return res

    def _get_rows_invoice(self, cr, uid, ids,data, context=None):
        """
        Return list to generate rows of the CSV file
        """
        start_date = data['start_date']
        end_date = data['end_date']
       
        # option = data['option']

              
        tz = '7 hours'
        query_where = ""

        if start_date :
            query_where += " AND so.date_order >= '%s' " % (start_date)
        if end_date :
            query_where += " AND so.date_order <= '%s' "  % (end_date)

      
        query="""
              select ai.number as inv,
                so.name as no_so,
                rp.name as partner,
                sol.name as des,
                sol.product_uom_qty as qty,
                sol.price_unit as unit_price,
                at.name as taxes,
                sol.discount as dis,
                aptl.days as pyment,
                apt.name as pyment2,
                to_char(so.date_order,'YYYY-MM-DD') as date,
                to_char(so.date_order + CAST(aptl.days||'Days' AS Interval), 'YYYY-MM-DD') as tgl_jatuh_tempo,
                rp.dealer_code as dealer_code

                from sale_order as so
                LEFT JOIN res_partner rp ON so.partner_id=rp.id
                LEFT JOIN sale_order_line sol ON so.id=sol.order_id
                LEFT JOIN product_product pro ON sol.product_id=pro.id
                LEFT JOIN sale_order_tax sot ON sol.id=sot.order_line_id
                LEFT JOIN account_tax at ON sot.tax_id=at.id
                LEFT JOIN account_payment_term apt ON so.payment_term=apt.id
                LEFT JOIN account_payment_term_line aptl ON apt.id=aptl.payment_id
                LEFT JOIN account_invoice ai ON so.name=ai.reference
                where so.division='Sparepart'
                and so.state in ('progress','done')
                and rp.name !='TOKO UMUM' %s

            """ %(query_where)
        cr.execute (query)
        res = cr.fetchall()

        rows = []
        for line in res:
            inv          = str(line[0]) if line[0] != None else ''
            no_so        = str(line[1]) if line[1] != None else ''
            partner      = str(line[2]) if line[2] != None else ''

            qty          = str(line[4])
            unit_price   = str(line[5])
            taxes        = str(line[6])
            dis          = str(line[7])
           
            pyment2      = str(line[9]) if line[9] != None else ''
            tgl_jatuh_tempo = str(line[11]) if line[11] != None else ''

            dealer_code = str(line[12]) if line[12] != None else ''

            sub_total = ((line[4] * line[5])/1.1)-((line[4] * line[5])/1.1)*float(dis)/100
            total = str(sub_total) if sub_total != None else ''
          

            spareparts = inv+";"+no_so+";"+partner+";"+line[3]+";"+line[3]+";"+qty+";"+unit_price+";"+taxes+";"+dis+";"+pyment2+";"+total+";"+line[10]+";"+tgl_jatuh_tempo+";"+dealer_code+";Sparepart"
            # sparepartx = str(spareparts).replace('"','')
            rows.append(list(
                {
                spareparts
                })
                )
        return rows





    def _get_rows_invoice_unit(self, cr, uid, ids,data, context=None):
        """
        Return list to generate rows of the CSV file
        """
        start_date = data['start_date']
        end_date = data['end_date']
       
        # option = data['option']

              
        tz = '7 hours'
        query_where = ""

        if start_date :
            query_where += " AND so.date_order >= '%s' " % (start_date)
        if end_date :
            query_where += " AND so.date_order <= '%s' "  % (end_date)

      
        query="""
              select ai.number as inv,
                so.name as no_so,
                rp.name as partner,
                sol.name as des,
                sol.product_uom_qty as qty,
                sol.price_unit as unit_price,
                at.name as taxes,
                sol.discount as dis,
                aptl.days as pyment,
                apt.name as pyment2,
                to_char(so.date_order,'YYYY-MM-DD') as date,
                to_char(so.date_order + CAST(aptl.days||'Days' AS Interval), 'YYYY-MM-DD') as tgl_jatuh_tempo,
                rp.dealer_code as dealer_code

                from sale_order as so
                LEFT JOIN res_partner rp ON so.partner_id=rp.id
                LEFT JOIN sale_order_line sol ON so.id=sol.order_id
                LEFT JOIN product_product pro ON sol.product_id=pro.id
                LEFT JOIN sale_order_tax sot ON sol.id=sot.order_line_id
                LEFT JOIN account_tax at ON sot.tax_id=at.id
                LEFT JOIN account_payment_term apt ON so.payment_term=apt.id
                LEFT JOIN account_payment_term_line aptl ON apt.id=aptl.payment_id
                LEFT JOIN account_invoice ai ON so.name=ai.reference
                where so.division='Unit'
                and so.state in ('progress','done')
                and rp.name !='TOKO UMUM' %s

            """ %(query_where)

        cr.execute (query)
        res = cr.fetchall()

        rows_unit = []
        for lines in res:
            inv          = str(lines[0]) if lines[0] != None else ''
            no_so        = str(lines[1]) if lines[1] != None else ''
            partner      = str(lines[2]) if lines[2] != None else ''

            qty          = str(lines[4])
            unit_price   = str(lines[5])
            taxes        = str(lines[6])
            dis          = str(lines[7])
           
            pyment2      = str(lines[9]) if lines[9] != None else ''
            tgl_jatuh_tempo = str(lines[11]) if lines[11] != None else ''

            dealer_code = str(lines[12]) if lines[12] != None else ''

            sub_total = ((lines[4] * lines[5])/1.1)-((lines[4] * lines[5])/1.1)*float(dis)/100
            total = str(sub_total) if sub_total != None else ''
          

            units = inv+";"+no_so+";"+partner+";"+lines[3]+";"+lines[3]+";"+qty+";"+unit_price+";"+taxes+";"+dis+";"+pyment2+";"+total+";"+lines[10]+";"+tgl_jatuh_tempo+";"+dealer_code+";Unit"
            # unitx = str(units).replace('"','')
            rows_unit.append(list(
                {
                units
                })
                )
        return rows_unit
