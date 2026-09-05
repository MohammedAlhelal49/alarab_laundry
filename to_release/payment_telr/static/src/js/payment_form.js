/** @odoo-module **/
import { rpc, RPCError } from '@web/core/network/rpc';
import paymentForm from '@payment/js/payment_form';

paymentForm.include({
	
	/**
         * Simulate a feedback from a payment provider and redirect the customer to the status page.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the provider
         * @param {number} providerId - The id of the provider handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {Promise}
         */
        async  _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
            if (providerCode !== 'telr') {
                await this._super(...arguments); 
                return;
            }

            const telr_payment_token = document.getElementById('telr_payment_token').value;
            return rpc('/payment/telr/process_payment',{
                    'processing_values': processingValues,
                    'telr_payment_token': telr_payment_token
            }).then(data => {
				$('#inlineFrame').empty();
                const iframe = '<iframe marginheight="0" marginwidth="0" id="terliframe" frameborder = "0" width="100%" height="450" src="'+data+'" sandbox="allow-forms allow-modals allow-popups-to-escape-sandbox allow-popups allow-scripts allow-top-navigation allow-same-origin"/>';			
				$('#inlineFrame').append(iframe);
				$('.o-main-components-container').hide();
            });
        },

		/**
         * Simulate a feedback from a payment provider and redirect the customer to the status page.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the provider
         * @param {number} providerId - The id of the provider handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {Promise}
         */
        
		async _processRedirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {

            if (providerCode !== 'telr') {
                await this._super(...arguments); 
                return;
            }
			
			const flowtype = processingValues.ivp_framed
			if(flowtype == 2){
				const iframe = '<iframe marginheight="0" marginwidth="0" id="terliframe" frameborder = "0" width="100%" height="450" src="'+processingValues.api_url+'" sandbox="allow-forms allow-modals allow-popups-to-escape-sandbox allow-popups allow-scripts allow-top-navigation allow-same-origin"/>';			
				$('#inlineFrame').append(iframe);
				$('.o-main-components-container').hide();				
			}else{
				const $redirectForm = $(processingValues.redirect_form_html).attr('id', 'o_payment_redirect_form');
				$redirectForm[0].setAttribute('target', '_top');
				$(document.getElementsByTagName('body')[0]).append($redirectForm);
				$redirectForm.submit();
			}				
        },
		
		
		/**
         * Prepare the inline form of Demo for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the selected payment option's provider
         * @param {integer} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
		async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) { 
            if (providerCode !== 'telr') {
                await this._super(...arguments); 
                return;
            } 
			
			$('#inlineFrame').empty();
			
			return rpc('/payment/telr/getinfo',{ 
                    'provider_id': providerId,
					'currency_id': this.paymentContext.currencyId,
					'partner_id':this.paymentContext.partnerId,                
            }).then(data => {
				console.log(data)
				if(data.telr_payment_mode == 10){
					
					this._setPaymentFlow('direct');
					
					var store_id = data.store_id;
					var currency = data.currency_name;
					var test_mode = data.test_mode;
					var saved_cards = data.saved_cards;
					var frameHeight = data.frame_height;
					var language = data.language;
					window.telrInit = false;
					
					
					var telrMessage = {
						"message_id": "init_telr_config",
						"store_id": store_id,
						"currency": currency,
						"test_mode": test_mode,
						"saved_cards": saved_cards,
						"appearance": {
							"labels": 0,  // 1->show labels ,0->hide labels
							"logos": 0,   // 1->show logos, 0->hide logos
							"borders": 0,  // 1->show borders , 0->hide borders
							"dropdowns": 0 // 1->show dropdowns for month and year, 0->hide dropdowns and show MM/YY field
						}
					}
					
					var iframeUrl = "https://secure.telr.com/jssdk/v2/token_frame.html?token=" + Math.floor((Math.random() * 9999999999) + 1) + "&lang=" + language;
					var iframeHtml = ' <iframe id="telr_iframe" src= "' + iframeUrl + '" style="width: 100%; height: '+frameHeight+'px; border: 0;" sandbox="allow-forms allow-modals allow-popups-to-escape-sandbox allow-popups allow-scripts allow-top-navigation allow-same-origin"></iframe>';
					iframeHtml +=  '<input id="telr_payment_token" type="hidden" name="telr_payment_token"/>';
					$('#inlineFrame').append(iframeHtml);

					if (typeof window.addEventListener != 'undefined') {
						window.addEventListener('message', function(e) {
							var message = e.data;
							 if(message != ""){
								var isJson = true;
								try {
									JSON.parse(str);
								} catch (e) {
									isJson = false;
								}
								if(isJson || (typeof message === 'object' && message !== null)){
									var telrMessage = (typeof message === 'object') ? message : JSON.parse(message);
									if(telrMessage.message_id != undefined){
										switch(telrMessage.message_id){
											case "return_telr_token": 
												var payment_token = telrMessage.payment_token;
												console.log("Telr Token Received: " + payment_token);
												$("#telr_payment_token").val(payment_token);
											break;
										}
									}
								}
							}
							
						}, false);
						
					} else if (typeof window.attachEvent != 'undefined') { // this part is for IE8
						window.attachEvent('onmessage', function(e) {
							var message = e.data;
							 if(message != ""){
								 try {
									JSON.parse(str);
								} catch (e) {
									isJson = false;
								}
								if(isJson || (typeof message === 'object' && message !== null)){
									var telrMessage = (typeof message === 'object') ? message : JSON.parse(message);
									if(telrMessage.message_id != undefined){
										switch(telrMessage.message_id){
											case "return_telr_token": 
												var payment_token = telrMessage.payment_token;
												console.log("Telr Token Received: " + payment_token);
												$("#telr_payment_token").val(payment_token);
											break;
										}
									}
								}
							}
							
						});
					}

					jQuery(document).ready(function(){
						$('#telr_iframe').on('load', function(){
							var initMessage = JSON.stringify(telrMessage);
							setTimeout(function(){
								if(!window.telrInit){
									document.getElementById('telr_iframe').contentWindow.postMessage(initMessage,"*");
									window.telrInit = true;
								}
							}, 1500);
						});
					});
					
					$('input[data-provider-code="telr"]').each(function() {						
						var parentElement = $(this).closest('.d-flex');
						parentElement.find('.gap-1').removeClass('gap-1');
					});
				}
				
            });
        },
});
