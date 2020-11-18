openerp.purchase = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    instance.web.dealerspk = instance.web.dealerspk || {};
    instance.web.views.add('tree_dealer_spk_report', 'instance.web.dealerspk.QuickAddListView');
    instance.web.dealerspk.QuickAddListView = instance.web.ListView.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.branchs = [];
            this.products = [];
            this.current_branch = null;
            this.current_product = null;
            this.default_product = null;
            this.default_branch = null;
        },
        start:function(){
            var tmp = this._super.apply(this, arguments);
            var self = this;
            var defs = [];
            this.$el.parent().prepend(QWeb.render("DealerSpkAdd", {widget: this}));
            
            this.$el.parent().find('.oe_account_select_branch').change(function() {
                    self.current_branch = this.value === '' ? null : parseInt(this.value);
                    self.do_search(self.last_domain, self.last_context, self.last_group_by);
                });
            this.$el.parent().find('.oe_account_select_product').change(function() {
                    self.current_product = this.value === '' ? null : parseInt(this.value);
                    self.do_search(self.last_domain, self.last_context, self.last_group_by);
                });
            this.on('edit:after', this, function () {
                self.$el.parent().find('.oe_account_select_branch').attr('disabled', 'disabled');
                self.$el.parent().find('.oe_account_select_product').attr('disabled', 'disabled');
            });
            this.on('save:after cancel:after', this, function () {
                self.$el.parent().find('.oe_account_select_branch').removeAttr('disabled');
                self.$el.parent().find('.oe_account_select_product').removeAttr('disabled');
            });
            var mod = new instance.web.Model("dealer.spk.report", self.dataset.context, self.dataset.domain);
            defs.push(mod.call("default_get", [['branch_id','product_id'],self.dataset.context]).then(function(result) {
                
            }));
            defs.push(mod.call("list_branchs", []).then(function(result) {
                self.branchs = result;
            }));
            defs.push(mod.call("list_products", []).then(function(result) {
                self.products = result;
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
                    $(o).attr('selected',true);
                }
                self.$el.parent().find('.oe_account_select_branch').append(o);
            }
            self.$el.parent().find('.oe_account_select_product').children().remove().end();
            self.$el.parent().find('.oe_account_select_product').append(new Option('', ''));
            for (var i = 0;i < self.products.length;i++){
                o = new Option(self.products[i][1], self.products[i][0]);
                self.$el.parent().find('.oe_account_select_product').append(o);
            }    
            self.$el.parent().find('.oe_account_select_product').val(self.current_product).attr('selected',true);
            return self.search_by_branch_product();
        },
        search_by_branch_product: function() {
            var self = this;
            var domain = [];
            if (self.current_branch !== null) domain.push(["branch_id", "=", self.current_branch]);
            if (self.current_product !== null) domain.push(["product_id", "=", self.current_product]);
            self.last_context["branch_id"] = self.current_branch === null ? false : self.current_branch;
            if (self.current_product === null) delete self.last_context["product_id"];
            else self.last_context["product_id"] =  self.current_product;
            
            var compound_domain = new instance.web.CompoundDomain(self.last_domain, domain);
            self.dataset.domain = compound_domain.eval();
            return self.old_search(compound_domain, self.last_context, self.last_group_by);
        },
    });
};
