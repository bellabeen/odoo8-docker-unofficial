    @api.model
    def _auto_init(self):
        res = super(ReportWeeklyKonsolidate, self)._auto_init()
        self._cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = 'teds_report_weekly_konsolidate_state_date_index'")
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX teds_report_weekly_konsolidate_state_date_index ON teds_report_weekly_konsolidate  USING btree (state,start_date,end_date)')
        
    
        self._cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = 'dealer_sale_order_state_date_order_index'")
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX dealer_sale_order_state_date_order_index ON dealer_sale_order USING btree (state,date_order)')
        return res
