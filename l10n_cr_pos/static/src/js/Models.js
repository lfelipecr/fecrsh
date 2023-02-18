odoo.define('l10n_cr_pos.Models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');

    models.load_fields('pos.payment.method', ['payment_method_id','account_payment_term_id','is_refund']);
    models.load_fields('res.company', ['frm_ws_ambiente','county_id','district_id','neighborhood_id']);
    models.load_fields('res.partner', ['identification_id','county_id','district_id','neighborhood_id','payment_methods_id','property_payment_term_id']);

    models.load_models([{
        model:  'l10n_latam.identification.type',
        fields: ['code','name','notes'],
        loaded: function(self, identification){
            self.list_identification = identification;
            for(var i=0;i<identification.length;i++){
                self.list_identification[i] = identification[i];
            }
        },
    }]);

    models.load_models([{
        model:  'res.country.county',
        fields: ['code','name','state_id'],
        loaded: function(self, county){
            self.list_county = county;

        },
    }]);

    models.load_models([{
        model:  'res.country.district',
        fields: ['code','name','county_id'],
        loaded: function(self, district){
            self.list_district = district;

        },
    }]);

    models.load_models([{
        model:  'res.country.neighborhood',
        fields: ['code','name','district_id'],
        loaded: function(self, neighborhood){
            self.list_neighborhood = neighborhood;
        },
    }]);

     models.load_models([{
        model:  'account.payment.term',
        fields: ['name','active','line_ids','company_id'],
        loaded: function(self, payment_term){
            self.list_payment_terms_ids = payment_term;
        },
    }]);

    models.load_models([{
        model:  'payment.methods',
        fields: ['active','name','notes'],
        loaded: function(self, payment_methods){
            self.list_payment_methods_ids = payment_methods;
        },
    }]);

});
