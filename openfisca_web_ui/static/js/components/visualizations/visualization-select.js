/** @jsx React.DOM */
'use strict';

var React = require('react');


var VisualizationSelect = React.createClass({
  propTypes: {
    onChange: React.PropTypes.func.isRequired,
    value: React.PropTypes.string,
    visualizations: React.PropTypes.array.isRequired,
  },
  handleChange: function(event) {
    this.props.onChange(event.target.value);
  },
  render: function() {
    var options = this.props.visualizations.map(function(visualization) {
      return <option key={visualization.slug} value={visualization.slug}>{visualization.title}</option>;
    });
    return (
      <select className="form-control" onChange={this.handleChange} value={this.props.value}>
        {options}
        <option value="json">JSON</option>
      </select>
    );
  }
});

module.exports = VisualizationSelect;