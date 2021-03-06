define([
	'jquery',
	'backbone'
], function($, Backbone) {
	'use strict';

	var AcceptCnilConditionsModalV = Backbone.View.extend({
		el: '#accept-cnil-conditions-modal',
		events: {
			'change input[name="accept-checkbox"]': 'updateAcceptButton',
			'click button[name="reject"]': 'logout'
		},
		initialize: function () {
			this.$el.modal({
				backdrop: 'static',
				keyboard: false,
				show: true
			});
			this.updateAcceptButton();
		},
		logout: function() {
			navigator.id.logout();
		},
		updateAcceptButton: function() {
			var $button = this.$el.find('button[name="accept"]');
			if (this.$el.find('input[name="accept-checkbox"]').is(':checked')) {
				$button.removeAttr('disabled');
			} else {
				$button.attr('disabled', 'disabled');
			}
		}
	});

	return AcceptCnilConditionsModalV;
});
