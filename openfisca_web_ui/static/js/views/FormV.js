define([
	'jquery',
	'underscore',
	'backbone',

	'backendServiceM',
	],
	function ($, _, Backbone, backendServiceM) {
		var FormV = Backbone.View.extend({
			events: {
				'keypress input': 'submit',
				'click :input[type="submit"]': 'submit',
				'click .nav-tabs a': 'changeTab',
			},
			model: backendServiceM,
			el: '#form-wrapper',

			initialize: function () {
				console.log('FormV.initialize');
				this.listenTo(this.model, 'change:formData', this.render);
			},
			changeTab: function(evt) {
				evt.preventDefault();
				var tabName = $(evt.target).data('tab-name');
				this.model.fetchForm(tabName, $.proxy(this.model.simulate, this.model));
			},
			render: function () {
				console.log('FormV.render');
				var data = this.model.get('formData');
				this.$el.html(data);
				return this;
			},
			submit: function(evt) {
				if (evt.type == 'keypress' && evt.keyCode !== 13) {
					return;
				}
				evt.preventDefault();
				var $form = this.$el.find('form');
				var formDataStr = $form.serialize();
				if (evt.type == 'click') {
					// Add clicked button to form data.
					var $button = $(evt.target);
					var name = $button.attr('name');
					if ( ! _.isUndefined(name)) {
						var value = $button.attr('value');
						formDataStr += '&' + name + '=' + value;
					}
				}
				this.model.validateForm(formDataStr, $.proxy(this.model.simulate, this.model));
			}
		});
		return FormV;
	}
);