## -*- coding: utf-8 -*-


## OpenFisca -- A versatile microsimulation software
## By: OpenFisca Team <contact@openfisca.fr>
##
## Copyright (C) 2011, 2012, 2013, 2014 OpenFisca Team
## https://github.com/openfisca
##
## This file is part of OpenFisca.
##
## OpenFisca is free software; you can redistribute it and/or modify
## it under the terms of the GNU Affero General Public License as
## published by the Free Software Foundation, either version 3 of the
## License, or (at your option) any later version.
##
## OpenFisca is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.


<%!
import datetime

from openfisca_web_ui import model, urls
%>


<%inherit file="/admin.mako"/>


<%namespace name="render_legislation" file="/legislations/render-legislation.mako"/>


<%def name="appconfig_script()" filter="trim">
    <%render_legislation:appconfig_script/>
</%def>


<%def name="breadcrumb_content()" filter="trim">
            <%parent:breadcrumb_content/>
            <li><a href="${urls.get_url(ctx, 'admin')}">${_(u"Admin")}</a></li>
            <li><a href="${model.Legislation.get_admin_class_url(ctx)}">${_(u"Legislations")}</a></li>
            <li class="active">${legislation.get_title(ctx)}</li>
</%def>


<%def name="container_content()" filter="trim">
<%
    user = model.get_user(ctx, check = True)
    dated_legislation = legislation.json is not None and legislation.json.get('datesim') is not None
    owner_or_admin = model.is_admin(ctx) or user._id == legislation.author_id
    editable = owner_or_admin and dated_legislation
%>\
        <div class="page-header">
            <h1>${_('Legislation')} <small>${legislation.get_title(ctx)}</small></h1>
        </div>
        <div class="panel panel-default">
            <div class="panel-heading">
                <h2 class="panel-title">
    % if owner_or_admin:
                    <a class="btn btn-default btn-sm" href="${legislation.get_admin_url(ctx, 'edit')}">
    % else:
                    <a class="btn btn-default btn-xs" data-toggle="modal" data-target="#modal-duplicate-and-edit" \
href="#" title="${_(u'Edit') if owner_or_admin else _(u'Duplicate and edit')}">
    % endif:
                        <span class="glyphicon glyphicon-cog"></span>
                    </a>
                    ${legislation.get_title(ctx)}
                </h2>
            </div>
            <ul class="list-group">
                <li class="list-group-item">
                    <%self:view_fields/>
                </li>
                <li class="list-group-item">
                    ${self.view_content(user = user)}
                </li>
            </ul>
            <div class="panel-footer">
                <div class="btn-toolbar">
                    <a class="btn btn-default" href="${legislation.get_api1_url(ctx, 'json')}">
                        ${_(u'View as JSON')}
                    </a>
    % if owner_or_admin:
                    <a class="btn btn-danger"  href="${legislation.get_admin_url(ctx, 'delete')}">
                        <span class="glyphicon glyphicon-trash"></span> ${_('Delete')}
                    </a>
    % endif
                </div>
            </div>
        </div>
</%def>


<%def name="css()" filter="trim">
    <%parent:css/>
    <link href="${urls.get_url(ctx, u'bower/x-editable/dist/bootstrap3-editable/css/bootstrap-editable.css')}" \
media="screen" rel="stylesheet">
</%def>


<%def name="modals()" filter="trim">
<%
    user = model.get_user(ctx, check = True)
    dated_legislation = legislation.json is not None and legislation.json.get('datesim') is not None
    owner_or_admin = model.is_admin(ctx) or user._id == legislation.author_id
    editable = owner_or_admin and dated_legislation
%>\
    <%parent:modals/>
    <%render_legislation:modal_change_legislation_date/>
    % if not editable:
    <%render_legislation:modal_duplicate_and_edit/>
    % endif
</%def>


<%def name="title_content()" filter="trim">
${legislation.get_title(ctx)} - ${parent.title_content()}
</%def>


<%def name="view_fields()" filter="trim">
        <dl class="dl-horizontal">
<%
    value = legislation.description
%>\
    % if value is not None:
            <dt>${_("Description")}</dt>
            <dd>${legislation.description}</dd>
    % endif
<%
    value = legislation.url
%>\
    % if value is not None:
            <dt>${_("Source URL")}</dt>
            <dd><a href="${value}">${value}</a></dd>
    % endif
    % if dated_legislation:
<%
        value = legislation.json['datesim']
%>\
        % if value is not None:
            <dt>${_("Dated legislation")}</dt>
            <dd>${value}</dd>
        % endif
    % elif legislation.json is not None:
<%
        value = legislation.json.get('from')
%>\
        % if value is not None:
            <dt>${_("Begin date")}</dt>
            <dd>${value}</dd>
        % endif
<%
        value = legislation.json.get('to')
%>\
        % if value is not None:
            <dt>${_("End date")}</dt>
            <dd>${value}</dd>
        % endif
    % endif
<%
    value = legislation.updated
%>\
    % if value is not None:
            <dt>${_("Updated")}</dt>
            <dd>${value}</dd>
    % endif
<%
    value = legislation.published
%>\
    % if value is not None:
            <dt>${_("Published")}</dt>
            <dd>${value}</dd>
        </dl>
    % endif
</%def>


<%def name="view_content(user = None)" filter="trim">
<%
    dated_legislation = legislation.json is not None and legislation.json.get('datesim') is not None
    if user is not None:
        owner_or_admin = model.is_admin(ctx) or user._id == legislation.author_id
        editable = owner_or_admin and dated_legislation
    else:
        owner_or_admin = False
        editable = False

    value = legislation.json
%>\
    % if value is not None:
        % if editable:
        <p>
            <strong>${_('Editable content')}</strong>
        </p>
        <div class="alert alert-info">
        % endif:
        <div class="row">
            <div class="col-lg-8">
        % if dated_legislation_json is not None:
                ${render_legislation.render_dated_legislation_node(node = dated_legislation_json, editable = editable)}
        % elif value.get('datesim') is not None:
                ${render_legislation.render_dated_legislation_node(node = value, editable = editable)}
        % else:
                ${render_legislation.render_legislation_node(node = value)}
        % endif:
            </div>
        </div>
        % if editable:
        </div>
        % endif:
        <div class="row">
            <div class="col-lg-8">
                <div class="buttons">
                    <button type="button" class="btn btn-default btn-xs btn-expand-all">
                        ${_('Open all')}
                    </button>
                    <button type="button" class="btn btn-default btn-xs btn-collapse-all">
                        ${_('Close all')}
                    </button>
            % if editable is False:
                % if owner_or_admin:
                    <a class="btn btn-primary btn-xs" href="${legislation.get_user_url(ctx, 'edit')}">
                        <span class="glyphicon glyphicon-lock"></span>
                        ${_(u'Edit content')}
                    </a>
                % elif user is not None and user.email is not None:
                    <a class="btn btn-primary btn-xs" data-toggle="modal" data-target="#modal-duplicate-and-edit" \
href="#">
                        <span class="glyphicon glyphicon-lock"></span>
                        ${_(u'Edit content')}
                    </a>
                % endif
            % endif:
            % if dated_legislation:
                    ${_('Legislation for')}
                    ${datetime.datetime.strftime(date, '%d/%m/%Y')}
            % elif date:
                    ${_('Legislation for')}
                    <a data-toggle="modal" data-target="#modal-change-legislation-date" href="#">
                        ${datetime.datetime.strftime(date, '%d/%m/%Y')}
                    </a>
            % else:
                    ${_('Legislation from {} to {}').format(value.get('from'), value.get('to'))}
            % endif
                </div>
            </div>
        </div>
    % endif
</%def>
