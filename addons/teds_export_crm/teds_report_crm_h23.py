    def _print_csv_report_kpb(self, cr, uid, ids, data, context=None):
        
        data = self.read(cr, uid, ids,context=context)[0]
        this = self.browse(cr, uid, ids)[0]
        rows = self._get_rows_account(cr, uid, ids, data, context)       
        file_data = StringIO()
        try:
            writer = AccountUnicodeWriter(file_data)
            writer.writerows(rows)
            file_value = file_data.getvalue()
            out=base64.encodestring(file_value)
            filename = 'Report KPB'
            self.write(cr, uid, ids,
                       {'state_x':'get', 'data_x':out, 'name': filename +".txt"},
                       context=context)
        finally:
            file_data.close()



    def excel_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        data = self.read(cr, uid, ids,context=context)[0]
        if len(data['branch_ids']) == 0 :
            data.update({'branch_ids': self._get_branch_ids(cr, uid, context)})

        self._print_excel_report_kpb(cr, uid, ids, data, context=context)
        
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'teds_report_kpb', 'view_report_kpb')

        form_id = form_res and form_res[1] or False
        return {
            'name': _('Download XLS'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wtc.report.kpb',
            'res_id': ids[0],
            'view_id': False,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current'
        }


    def _print_excel_report_kpb(self, cr, uid, ids, data, context=None):

        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)        
        # workbook = self.add_workbook_format(cr, uid, workbook)
        wbf=self.wbf

        date= self._get_default(cr, uid, date=True, context=context)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        company_name = self._get_default(cr, uid, user=True,context=context).company_id.name
        user = self._get_default(cr, uid, user=True, context=context).name
        
        filename = 'Report KPB '+str(date)+'.xlsx'        
        worksheet.write('A1', company_name , wbf['company'])
        worksheet.write('A2', 'Report KPB' , wbf['title_doc'])
        worksheet.write('A3', ' ' , wbf['company'])
       
        workbook.close()
        out=base64.encodestring(fp.getvalue())
        self.write(cr, uid, ids, {'state_x':'get', 'data_x':out, 'name': filename}, context=context)
        fp.close()

wtc_report_kpb()
