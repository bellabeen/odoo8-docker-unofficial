openerp.purchase = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    instance.web.reportstock = instance.web.reportstock || {};
    instance.web.views.add('tree_report_stock', 'instance.web.reportstock.QuickAddListView');
    instance.web.reportstock.QuickAddListView = instance.web.ListView.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.branchs = [];
            this.current_branch = null;
            this.default_branch = null;
        },
        start:function(){
            var tmp = this._super.apply(this, arguments);
            var self = this;
            var defs = [];
            this.$el.parent().prepend(QWeb.render("ReportStockAdd", {widget: this}));
            
            this.$el.parent().find('.oe_account_select_branch').change(function() {
                    self.current_branch = this.value === '' ? null : parseInt(this.value);
                    self.do_search(self.last_domain, self.last_context, self.last_group_by);
                });
          
            this.on('edit:after', this, function () {
                self.$el.parent().find('.oe_account_select_branch').attr('disabled', 'disabled');
            });
            this.on('save:after cancel:after', this, function () {
                self.$el.parent().find('.oe_account_select_branch').removeAttr('disabled');
            });
            var mod = new instance.web.Model("wtc.report.stock.tree", self.dataset.context, self.dataset.domain);
            defs.push(mod.call("default_get", [['branch_id'],self.dataset.context]).then(function(result) {
            self.current_branch = result['branch_id'];
                
            }));
            defs.push(mod.call("list_branchs", []).then(function(result) {
                self.branchs = result;
            }));
           
            return $.when(tmp, defs);
        },
        do_search: function(domain, context, group_by) {
            var self = this;
            this.last_domain = domain;
            this.last_context = context;
            this.last_group_by = group_by;
            this.old_search = _.bind(this._super, this);
            var o;
            self.$el.parent().find('.oe_account_select_branch').children().remove().end();
            self.$el.parent().find('.oe_account_select_branch').append(new Option('', ''));
            for (var i = 0;i < self.branchs.length;i++){
                o = new Option(self.branchs[i][1], self.branchs[i][0]);
                if (self.branchs[i][0] === self.current_branch){
	                o = new Option(self.branchs[i][1], self.branchs[i][0]);
	                self.$el.parent().find('.oe_account_select_branch').append(o);
                }
                self.$el.parent().find('.oe_account_select_branch').append(o);
            }
            self.$el.parent().find('.oe_account_select_branch').val(self.current_branch).attr('selected',true);
            return self.search_by_branch_product();
        },
        search_by_branch_product: function() {
            var self = this;
            var domain = [];
            if (self.current_branch !== null) domain.push(["branch_id", "=", self.current_branch]);
           	if (self.current_branch == null) domain.push(["branch_id", "=", self.current_branch]);
            
            var compound_domain = new instance.web.CompoundDomain(self.last_domain, domain);
            self.dataset.domain = compound_domain.eval();
            return self.old_search(compound_domain, self.last_context, self.last_group_by);
        },
    });
};
