odoo.define('l10n_cr_pos.PaymentScreen', function(require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const session = require('web.session');
    const { useListener } = require('web.custom_hooks');
    var models = require('point_of_sale.models');


    models.PosModel = models.PosModel.extend({
        f_tipo_documento: function () {
            return true;
        },
    });

    var posorder_super = models.Order.prototype;
	models.Order = models.Order.extend({
		initialize: function(attr, options) {
			this.envio_hacienda = this.envio_hacienda || false;
			posorder_super.initialize.call(this,attr,options);
		},
		export_for_printing: function () {
            var result = posorder_super.export_for_printing.apply(this, arguments);
            result.tipo_documento = this.get_tipo_documento();
            result.numero_electronico = this.get_numero_electronico();
            result.secuencia = this.get_secuencia();
            result.envio_hacienda = this.get_envio_hacienda();
            return result;
        },

		export_as_JSON: function(){
			var loaded = posorder_super.export_as_JSON.apply(this, arguments);
			loaded.envio_hacienda = this.envio_hacienda || false;
			return loaded;
		},
        set_envio_hacienda: function (envio_hacienda) {
            this.envio_hacienda = envio_hacienda;
        },
        get_envio_hacienda: function () {
            return this.envio_hacienda;
        },
        set_tipo_documento: function (tipo_documento) {
            this.tipo_documento = tipo_documento;
        },
        get_tipo_documento: function () {
            return this.tipo_documento;
        },

        set_numero_electronico: function (numero_electronico) {
            this.numero_electronico = numero_electronico;
        },
        get_numero_electronico: function () {
            return this.numero_electronico;
        },

        set_secuencia: function (secuencia) {
            this.secuencia = secuencia;
        },
        get_secuencia: function () {
            return this.secuencia;
        },

        //MÉTODO PARA CONSULTAR
        wait_for_push_order: function () {
            var result = posorder_super.wait_for_push_order.apply(this, arguments);
            result = Boolean(result || this.pos.f_tipo_documento());
            return result;
        },


	});


    const PaymentScreenExtend = PaymentScreen =>
        class extends PaymentScreen {

            constructor() {
				super(...arguments);
				this.show_envio_hacienda = this.show_envio_hacienda();
				useListener('envio-hacienda', this.envio_hacienda_action);
			}
			show_envio_hacienda(){
                var self = this;
                var envio = self.env.pos.config.show_send_hacienda;
                return envio;
            }
			envio_hacienda_action() {
                var self = this;
                var order = this.env.pos.get_order();
                var check_sent_hacienda = $("#check_sent_hacienda")[0].checked;
                var enviar = false;
                if (check_sent_hacienda && self.show_envio_hacienda){
                    enviar = true;
                }
                order.set_envio_hacienda(enviar);
                var a =1;

			}

            async _postPushOrderResolve(order, order_server_ids) {
                try {
                    if (this.env.pos.f_tipo_documento()) {
                        const result = await this.rpc({
                            model: 'pos.order',
                            method: 'search_order',
                            args: [order.uid],
                        });
                        order.set_tipo_documento(JSON.parse(result).tipo_documento || false);
                        order.set_secuencia(JSON.parse(result).sequence || false);
                        order.set_numero_electronico(JSON.parse(result).number_electronic || false);
                        //Imprime en consola.
                        console.log(JSON.parse(result).tipo_documento || false)
                        console.log(JSON.parse(result).sequence || false)
                        console.log(JSON.parse(result).number_electronic || false)
                    }
                } finally {
                    return super._postPushOrderResolve(...arguments);
                }
            }


            validaciones_einvoice(){
                 //Validaciones en POS para facturación electrónica costa rica.
                 var t = this;
                 var currentOrder = t.currentOrder
                 var currentOrder_client = currentOrder.changed.client;
                 var company_id = t.env.pos.company;
                 var pos_config = t.env.pos.config;

                 if (company_id.frm_ws_ambiente != undefined || company_id.frm_ws_ambiente != false){
                     //Validación para la compañia
                     if(company_id.phone == undefined || company_id.phone == false){
                        swal('Aviso.','La compañia debe tener un número de teléfono !','info');
                        return false;
                     }
                     if(company_id.state_id == undefined || company_id.state_id == false){
                        swal('Aviso.','La compañia debe tener una provincia !','info');
                        return false;
                     }
                      if(company_id.county_id == undefined || company_id.county_id == false){
                        swal('Aviso.','La compañia debe tener un cantón !','info');
                        return false;
                      }
                      if(company_id.district_id == undefined || company_id.district_id == false){
                        swal('Aviso.','La compañia debe tener un distrito !','info');
                        return false;
                      }
                      if(company_id.neighborhood_id == undefined || company_id.neighborhood_id == false){
                        swal('Aviso.','La compañia debe tener un barrio !','info');
                        return false;
                      }

                     //Validación para la configuración de POS

                     if(pos_config.sucursal == undefined || pos_config.sucursal == false){
                        swal('Aviso.','La configuración del POS debe tener una sucursal !','info');
                        return false;
                     }
                     if(pos_config.terminal == undefined || pos_config.terminal == false){
                        swal('Aviso.','La configuración del POS debe tener un terminal !','info');
                        return false;
                     }
                      if(pos_config.sequence_fe_id == undefined || pos_config.sequence_fe_id == false){
                        swal('Aviso.','La configuración del POS debe tener una secuencia para facturación !','info');
                        return false;
                     }
                      if(pos_config.sequence_nc_id == undefined || pos_config.sequence_nc_id == false){
                        swal('Aviso.','La configuración del POS debe tener una secuencia para facturación con nota de crédito !','info');
                        return false;
                     }
                      if(pos_config.sequence_te_id == undefined || pos_config.sequence_te_id == false){
                        swal('Aviso.','La compañia debe tener un barrio !','info');
                        return false;
                     }

                    //Validación para la el cliente
                     if(currentOrder_client && company_id){
                        var currentOrder_client_id = currentOrder_client.id;
                        if (currentOrder_client_id == company_id.id){
                            swal('Sugerencia.','Asegúrese que el cliente seleccionado sea diferente a la compañia !','info');
                            return false;
                        }

                         //Validación para la compañia
                         if(currentOrder_client.phone == undefined || currentOrder_client.phone == false){
                            swal('Aviso.','El cliente debe tener un número de teléfono !','info');
                            return false;
                         }
                         if(currentOrder_client.state_id == undefined || currentOrder_client.state_id == false){
                            swal('Aviso.','El cliente debe tener una provincia !','info');
                            return false;
                         }
                          if(currentOrder_client.county_id == undefined || currentOrder_client.county_id == false){
                            swal('Aviso.','El cliente debe tener un cantón !','info');
                            return false;
                          }
                          if(currentOrder_client.district_id == undefined || currentOrder_client.district_id == false){
                            swal('Aviso.','El cliente debe tener un distrito !','info');
                            return false;
                          }
                          if(currentOrder_client.neighborhood_id == undefined || currentOrder_client.neighborhood_id == false){
                            swal('Aviso.','El cliente debe tener un barrio !','info');
                            return false;
                          }
                          if(currentOrder_client.email == undefined || currentOrder_client.email == false){
                            swal('Aviso.','El cliente debe tener un email !','info');
                            return false;
                          }
                          if(currentOrder_client.identification_id == undefined || currentOrder_client.identification_id == false){
                            swal('Aviso.','El cliente debe tener un tipo de identificación/documento !','info');
                            return false;
                          }
                          if(currentOrder_client.vat == undefined || currentOrder_client.vat == false){
                            swal('Aviso.','El cliente debe tener un número de identificación/documento !','info');
                            return false;
                          }
                     }

                     //Validación para las opciones de pago
                     var paymentlines = currentOrder.paymentlines;
                     if(paymentlines){
                        for(var i=0; i < paymentlines.models.length; i++){
                            var paid = paymentlines.models[i];
                            if (paid){
                                var payment_method = paid.payment_method;
                                if(payment_method){
                                    if(payment_method.account_payment_term_id == undefined || payment_method.account_payment_term_id == false){
                                        swal('Revisar.','Estimado usuario, es necesario que la opción de pago seleccionado tenga configurado un término de pago','info');
                                        return false;
                                    }
                                    if(payment_method.account_payment_term_id == undefined || payment_method.account_payment_term_id == false){
                                        swal('Revisar.','Estimado usuario, es necesario que la opción de pago seleccionado tenga configurado un método de pago','info');
                                        return false;
                                    }
                                }
                            }
                        }
                     }

                     return true; //En caso no haya ningún problema con las validaciones retorna True
                 }else{
                    return true
                 }
            }

            async validateOrder(isForceValidate) {
                 var t = this;
                 var res = t.validaciones_einvoice();
                 if(res){
                     swal({
                          title: "Estimado " + t.env.pos.employee.name + ', ¿Seguro que deseas continuar?',
                          text: "No podrás deshacer este paso.. ",
                          icon: "warning",
                          buttons: ["No seguiré", "Continuar!"],
                        }
                     ).then((value) => {
                         if (value) {
                             super.validateOrder(isForceValidate);
                          } else {
                            console.log("No hacer nada...");
                          }
                    });
                 }else{
                    return res;
                 }
            }



        };

    Registries.Component.extend(PaymentScreen, PaymentScreenExtend);

    return PaymentScreen;
});
