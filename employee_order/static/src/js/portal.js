odoo.define('employee_order.portal', function (require) {
'use strict';

    var publicWidget = require('web.public.widget');
    const Dialog = require('web.Dialog');
    const {_t, qweb} = require('web.core');
    const ajax = require('web.ajax');

    publicWidget.registry.portalOrderDetails = publicWidget.Widget.extend({
        selector: '.o_portal_order_details',
        events: {
            'change select[name="supplier_id"]': '_onSupplierChange',
            'change select[name="product_id"]': '_onProductChange',
            'change input[name="qty"]': '_onProductQtyChange',
            'input input[name="qty"]': '_onProductQtyinput',
            'change input[name="attachment"]': '_onAttachmentinput',
        },

        start: function () {
            var def = this._super.apply(this, arguments);
            this.data = {};
            this.customTaxusage = false;
            this.selectedProductDetails = false;
            this.selectedSupplier = false;
            if ($('input[name="customtax"]').is(":checked")){
                this.customTaxusage = true;
            }
            return def;
        },
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         */
         _renderSupplier: function (results) {
            var self = this;
           console.log(results);
           if (results){
              if (results[0]['seller_ids']){
                this._rpc({
                model: 'product.supplierinfo',
                method: 'search_read',
                args: [[['id', '=',results[0]['seller_ids']]], ['name','price','display_name']],
                kwargs: {
                    context: { show_price: true },
                },
                }).then(function (results) {
                    self._renderSupplierSelection(results);
                });
              }
           }
         },

         _renderSupplierSelection: function (results) {
            var self = this;
            var html = '<select name="supplier_id" t-attf-class="form-control">';
            html += '<option value="">Supplier...</option>';
            for (var i in results) {
                html += '<option data-id="' + results[i]['id'] + '" value="' + results[i]['price'] + '">' + results[i]['display_name'] + '</option>';
            }
            html += '</select> ';
            console.log(html);
            this.$('select[name="supplier_id"]').html(html);
         },

         _featchProDetails: function () {
            var self = this;
            var $product = this.$('select[name="product_id"]');
            var $productID = ($product.val() || 0);
            if ($productID){
                this._rpc({
                    model: 'product.product',
                    method: 'search_read',
                    args: [[['id', '=',parseFloat($productID)]], ['name','seller_ids','supplier_taxes_id']],
                }).then(function (results) {
                    self.selectedProductDetails = results;
                    self._renderSupplier(results);
                });
            }
            else{
                this.$('select[name="supplier_id"]').html('');
            }


        },

        _updatePriceForm: function () {
            var self = this;
            var $supplier = this.$('select[name="supplier_id"]');
            var $supplierValue = ($supplier.val() || 0);
            var $product = this.$('select[name="product_id"]');
            var $productID = ($product.val() || 0);
            var $Inputqty = this.$('input[name="qty"]');
            var $InputqtyVal = ($Inputqty.val()|| 0);
            if(! $supplierValue){
                alert("Please Select Supplier");
                return false;
            }
            if(! $productID){
                alert("Please Select Product");
                return false;
            }
            if(! $InputqtyVal){
                alert("Please Provide Amount to Buy");
                return false;
            }
            var tax_ids = [];
            if (this.customTaxusage){
                var tax_options = $('select[name="tax_id"] option');
                tax_ids = $.map(tax_options, e => $(e).val()).filter(value => value.trim().length > 0);
                tax_ids = $.map(tax_ids, function(n){ return parseFloat(n); });
            }
            else{
                tax_ids = this.selectedProductDetails[0]['supplier_taxes_id'];
            }
            if (tax_ids.length > 0){
                this.$('input[name="taxes_id"]').val(JSON.stringify(tax_ids));
                var args = [tax_ids, parseFloat($supplierValue), false, parseFloat($InputqtyVal)];
                this._rpc({
                    model: 'account.tax',
                    method: 'compute_all',
                    args: args,
                }).then(function (p) {
                    self.$('input[name="total_gross"]').val((p['total_included']).toFixed(2));
                    self.data = p;
                });
            }
            else{
                var total_included = (parseFloat($supplierValue) * parseFloat($InputqtyVal))
                this.$('input[name="total_gross"]').val((total_included).toFixed(2));
            }

        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _onSupplierChange: function () {
            this._updatePriceForm();
            var supplier = this.$('select[name="supplier_id"]').find(':selected').attr('data-id');
            if (supplier){
                this.$('input[name="supplier"]').val(supplier);
            }
            else{
                this.$('input[name="supplier"]').val('');
            }
        },

        _onProductChange: function () {

            this._featchProDetails();
            this._updatePriceForm();
        },

        _onProductQtyChange: function () {
            this._updatePriceForm();
        },

        _onProductQtyinput: function () {
            this.$('input[name="qty"]').val(this.$('input[name="qty"]').val().replace(/[^0-9]/g, ''));
        },

        _onAttachmentinput: function (){
            var files = $('input[name="attachment"]')[0].files;
            for (var i = 0; i < files.length; i++)
            {
                if (files[i].size > 5242880)
                    {
                       alert("Please Upload Less than 5 mb");
                       $('input[name="attachment"]').val('');
                    }
            }
        },

    });
});
