odoo.define('l10n_cr_pos.product_discount_service', function (require) {
    "use strict";
    var core = require('web.core');
    var rpc = require('web.rpc');
    var _t  = core._t;
    var models = require('point_of_sale.models');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    const { useListener } = require('web.custom_hooks');


    class ProductDiscountService extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            this.showPopup('ProductDiscountServicePopupWidget', {
                title: this.env._t('Descuento por Servicio.'),
                products: this.env.pos.attributes.selectedOrder.orderlines.models,
                tax_discount: this.env.pos.config.remove_tax_amount,
            });
        }
    }
    ProductDiscountService.template = 'ProductDiscountService';
    ProductScreen.addControlButton({
        component: ProductDiscountService,
        condition: function() {
            return this.env.pos.config.show_remove_tax;
        },
    });
    Registries.Component.add(ProductDiscountService);



    class ProductDiscountServicePopupWidget extends AbstractAwaitablePopup {
        constructor() {
			super(...arguments);
			//this.product = this.props.product;
		}
        remove_class(){
            //$('#reason').removeClass("text_shake");
            //$('#amount').removeClass("text_shake");
        }
        click_confirm(event){
            var self = this;
            var discount_general = self.env.pos.config.remove_tax_amount;
            var $element = $("#body_products_discount").find('tr');
            var dict = [];
            var count = 0;
            $element.each(function( index ) {
                var $el = $($element[index]);
                var checkbox = $("#checkbox_" + $el[0].id);
                var check = checkbox[0].checked;
                if(check){
                    dict.push(parseInt($el[0].id));
                }
                count = count + 1;
            });

            var lines = self.env.pos.attributes.selectedOrder.orderlines.models;

            var lines_not_discount = []
            for(var i = 0; i<lines.length; i++){
                if (dict.includes(lines[i].id)){
                    lines[i].is_tax_free = true ;
                    lines[i].tax_free_id = self.env.pos.config.remove_tax_amount[0] ;
                    lines[i].trigger('change',lines[i]);
                    //lines[i].set_discount(discount_general);
                }else{
                    lines_not_discount.push(lines[i]);
                }
            }

            if(lines_not_discount.length > 0 ){
                for(var i = 0; i<lines_not_discount.length; i++){
                    lines_not_discount[i].is_tax_free = false;
                    lines[i].tax_free_id = false
                    lines_not_discount[i].trigger('change', lines_not_discount[i]);

                    //lines_not_discount[i].set_discount(0);
                }
            }

            if (count==0){
                self.showPopup('AlertPopup', {
                    title: self.env._t('Ups'),
                    body: self.env._t("Asegúrese de tener productos para la venta.")
                });
            }

            if(dict.length > 0 ||  lines_not_discount.length >0){
                self.showPopup('AlertPopup', {
                    title: self.env._t('Bien'),
                    body: self.env._t("Se ha efectuado el descuento correctamente.")
                });
            }else{
                self.showPopup('AlertPopup', {
                    title: self.env._t('Ups'),
                    body: self.env._t("Asegúrese de tener productos para la venta.")
                });
            }
        }
    }

    ProductDiscountServicePopupWidget.template = 'ProductDiscountServicePopupWidget';
    Registries.Component.add(ProductDiscountServicePopupWidget);


    class AlertPopup extends AbstractAwaitablePopup {}
    AlertPopup.template = 'AlertPopup';
    Registries.Component.add(AlertPopup);


    var _super_orderline = models.Orderline.prototype;
	models.Orderline = models.Orderline.extend({
	    initialize: function(attr, options) {
            var self = this;
            this.is_tax_free = false;
            this.tax_free_id = false;
            _super_orderline.initialize.call(this,attr,options);
        },


		export_as_JSON: function(){
			var json = _super_orderline.export_as_JSON.call(this);
			json.is_tax_free = this.is_tax_free;
			return json;
		},
		init_from_JSON: function(json){
			_super_orderline.init_from_JSON.apply(this,arguments);
			this.is_tax_free = json.is_tax_free;
		},

		/*set_is_tax_free: function(is_tax_free){
			this.is_tax_free = is_tax_free;
		},

		get_is_tax_free: function(){
			return this.is_tax_free;
		},*/

		get_taxes: function(){
			if (this.is_tax_free){
				return [];
			}
			var taxes = _super_orderline.get_taxes.apply(this,arguments);
			return taxes;
		},
		get_applicable_taxes: function(){
			if (this.is_tax_free){
				return [];
			}
			var taxes = _super_orderline.get_applicable_taxes.apply(this,arguments);
			return taxes;
		},

		compute_all: function(taxes, price_unit, quantity, currency_rounding, handle_price_include=true){
			if (this.is_tax_free && this.tax_free_id){
			    var new_taxes = [];
			    var taxes = arguments[0];
			    if(taxes.length > 0){

			        for(var i=0; i<taxes.length; i++){
			            if(taxes[i].id == this.tax_free_id){

			            }else{
			                new_taxes.push(taxes[i])
			            }
			        }
			    }

				arguments[0] = new_taxes
			}
			//return this._super(taxes, price_unit, quantity, currency_rounding, no_map_tax);
			//return _super_order_line.compute_all.apply(this,arguments);
			return _super_orderline.compute_all.apply(this,arguments);
		},


	})

})
