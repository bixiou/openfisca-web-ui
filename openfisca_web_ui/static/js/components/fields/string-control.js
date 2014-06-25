/** @jsx React.DOM */
'use strict';

var React = require('react');

var CerfaField = require('./cerfa-field');


var StringControl = React.createClass({
  propTypes: {
    cerfaField: React.PropTypes.any,
    default: React.PropTypes.string,
    error: React.PropTypes.string,
    label: React.PropTypes.string.isRequired,
    name: React.PropTypes.string.isRequired,
    onChange: React.PropTypes.func.isRequired,
    required: React.PropTypes.bool,
    suggestion: React.PropTypes.string,
    value: React.PropTypes.string,
  },
  handleChange: function(event) {
    this.props.onChange(this.props.name, event.target.value);
  },
  render: function() {
    var label = this.props.label;
    if (this.props.required) {
      label += ' *';
    }
    return (
      <div>
        <label className="control-label" htmlFor={this.props.name}>{label}</label>
        <input
          className="form-control"
          id={this.props.name}
          onChange={this.handleChange}
          placeholder={this.props.suggestion || this.props.default}
          required={this.props.required}
          type="text"
          value={this.props.value}
        />
        {
          this.props.cerfaField ?
            <div className="col-md-8">
              <CerfaField value={this.props.cerfaFields} />
            </div>
            : null
        }
      </div>
    );
  }
});

module.exports = StringControl;