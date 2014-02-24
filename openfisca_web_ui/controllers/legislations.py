# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Controllers for legislations"""


import collections
import datetime
import json
import logging
import re
import requests

import pymongo
import webob
import webob.multidict

from .. import contexts, conf, conv, model, paginations, templates, urls, wsgihelpers


inputs_to_legislation_data = conv.pipe(
    conv.struct(
        dict(
            author_id = conv.base.input_to_uuid,
            datetime_begin = conv.base.function(lambda string: datetime.datetime.strptime(string, u'%d-%m-%Y')),
            datetime_end = conv.base.function(lambda string: datetime.datetime.strptime(string, u'%d-%m-%Y')),
            description = conv.cleanup_text,
            json = conv.pipe(
                conv.cleanup_line,
                conv.make_input_to_json(),
                ),
            url = conv.make_input_to_url(full = True),
            title = conv.pipe(
                conv.base.cleanup_line,
                conv.not_none,
                ),
            ),
        default = 'drop',
        ),
    conv.test(lambda struct: struct.get('url') is not None or struct.get('json') is not None),
    )
log = logging.getLogger(__name__)


@wsgihelpers.wsgify
def admin_delete(req):
    ctx = contexts.Ctx(req)
    legislation = ctx.node

    if not model.is_admin(ctx):
        return wsgihelpers.forbidden(ctx,
            explanation = ctx._("Deletion forbidden"),
            message = ctx._("You must  be an administrator to delete a legislation."),
            title = ctx._('Operation denied'),
            )

    if req.method == 'POST':
        legislation.delete(safe = True)
        return wsgihelpers.redirect(ctx, location = model.Legislation.get_admin_class_url(ctx))
    return templates.render(ctx, '/legislations/admin-delete.mako', legislation = legislation)


@wsgihelpers.wsgify
def admin_edit(req):
    ctx = contexts.Ctx(req)
    legislation = ctx.node

    if not model.is_admin(ctx):
        return wsgihelpers.forbidden(ctx,
            explanation = ctx._("Edition forbidden"),
            message = ctx._("You must  be an administrator to edit a legislation."),
            title = ctx._('Operation denied'),
            )

    if req.method == 'GET':
        errors = None
        inputs = dict(
            datetime_begin = datetime.datetime.strftime(legislation.datetime_begin, u'%d-%m-%Y'),
            datetime_end = datetime.datetime.strftime(legislation.datetime_end, u'%d-%m-%Y'),
            description = legislation.description,
            json = legislation.json,
            url = legislation.url,
            title = legislation.title,
        )
    else:
        assert req.method == 'POST'
        inputs = extract_legislation_inputs_from_params(ctx, req.POST)
        data, errors = inputs_to_legislation_data(inputs, state = ctx)
        if errors is None:
            data['slug'], error = conv.pipe(
                conv.input_to_slug,
                conv.not_none,
                )(data['title'], state = ctx)
            if error is not None:
                errors = dict(title = error)
        if errors is None:
            legislation_json, error = None, None
            if data['url'] is not None:
                legislation_json, error = conv.pipe(
                    conv.legislations.retrieve_legislation,
                    conv.legislations.validate_legislation_json,
                    )(data['url'], state = ctx)
            else:
                legislation_json, error = conv.legislations.validate_legislation_json(data['json'], state = ctx)
            if error is not None:
                errors = dict(json = error) if data['url'] is None else dict(url = error)
            else:
                data['json'] = legislation_json
        if errors is None:
            if model.Legislation.find(
                    dict(
                        _id = {'$ne': legislation._id},
                        slug = data['slug'],
                        ),
                    as_class = collections.OrderedDict,
                    ).count() > 0:
                errors = dict(email = ctx._('A legislation with the same name already exists.'))
        if errors is None:
            legislation.set_attributes(**data)
            legislation.compute_words()
            legislation.save(safe = True)

            # View legislation.
            return wsgihelpers.redirect(ctx, location = legislation.get_admin_url(ctx))
    return templates.render(ctx, '/legislations/admin-edit.mako', errors = errors, inputs = inputs,
        legislation = legislation)


@wsgihelpers.wsgify
def admin_index(req):
    ctx = contexts.Ctx(req)
    model.is_admin(ctx, check = True)

    assert req.method == 'GET'
    params = req.GET
    inputs = dict(
        advanced_search = params.get('advanced_search'),
        page = params.get('page'),
        sort = params.get('sort'),
        term = params.get('term'),
        )
    data, errors = conv.pipe(
        conv.struct(
            dict(
                advanced_search = conv.guess_bool,
                page = conv.pipe(
                    conv.input_to_int,
                    conv.test_greater_or_equal(1),
                    conv.default(1),
                    ),
                sort = conv.pipe(
                    conv.cleanup_line,
                    conv.test_in(['slug', 'updated']),
                    ),
                term = conv.base.input_to_words,
                ),
            ),
        conv.rename_item('page', 'page_number'),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.not_found(ctx, explanation = ctx._('Legislation search error: {}').format(errors))

    criteria = {}
    if data['term'] is not None:
        criteria['words'] = {'$all': [
            re.compile(u'^{}'.format(re.escape(word)))
            for word in data['term']
            ]}
    cursor = model.Legislation.find(criteria, as_class = collections.OrderedDict)
    pager = paginations.Pager(item_count = cursor.count(), page_number = data['page_number'])
    if data['sort'] == 'slug':
        cursor.sort([('slug', pymongo.ASCENDING)])
    elif data['sort'] == 'updated':
        cursor.sort([(data['sort'], pymongo.DESCENDING), ('slug', pymongo.ASCENDING)])
    legislations = cursor.skip(pager.first_item_index or 0).limit(pager.page_size)
    return templates.render(ctx, '/legislations/admin-index.mako', data = data, errors = errors,
        legislations = legislations, inputs = inputs, pager = pager)


@wsgihelpers.wsgify
def admin_new(req):
    ctx = contexts.Ctx(req)

    if not model.is_admin(ctx):
        return wsgihelpers.unauthorized(ctx,
            explanation = ctx._("Creation unauthorized"),
            message = ctx._("You must  be an administrator to create a legislation."),
            title = ctx._('Operation denied'),
            )

    legislation = model.Legislation()
    if req.method == 'GET':
        errors = None
        inputs = extract_legislation_inputs_from_params(ctx)
    else:
        assert req.method == 'POST'
        inputs = extract_legislation_inputs_from_params(ctx, req.POST)
        inputs['author_id'] = model.get_user(ctx)._id
        data, errors = inputs_to_legislation_data(inputs, state = ctx)
        if errors is None:
            data['slug'], error = conv.pipe(
                conv.input_to_slug,
                conv.not_none,
                )(data['title'], state = ctx)
            if error is not None:
                errors = dict(title = error)
        if errors is None:
            legislation_json, error = None, None
            if data['json'] is None:
                legislation_json, error = conv.pipe(
                    conv.legislations.retrieve_legislation,
                    conv.legislations.validate_legislation_json,
                    )(data['url'], state = ctx)
            else:
                legislation_json, error = conv.legislations.validate_legislation_json(data['json'], state = ctx)
            if error is not None:
                errors = dict(json = error) if data['url'] is None else dict(url = error)
            else:
                data['json'] = legislation_json
        if errors is None:
            if model.Legislation.find(
                    dict(
                        slug = data['slug'],
                        ),
                    as_class = collections.OrderedDict,
                    ).count() > 0:
                errors = dict(full_name = ctx._('A legislation with the same name already exists.'))
        if errors is None:
            legislation.set_attributes(**data)
            legislation.compute_words()
            legislation.save(safe = True)

            # View legislation.
            return wsgihelpers.redirect(ctx, location = legislation.get_admin_url(ctx))
    return templates.render(ctx, '/legislations/admin-new.mako', errors = errors, inputs = inputs,
        legislation = legislation)


@wsgihelpers.wsgify
def admin_view(req):
    ctx = contexts.Ctx(req)
    model.is_admin(ctx, check = True)
    legislation = ctx.node
    params = req.GET
    date, error = conv.pipe(
        conv.default(datetime.datetime.utcnow()),
        conv.condition(
            conv.test(lambda date: isinstance(date, basestring)),
            conv.pipe(
                conv.cleanup_line,
                conv.function(lambda date_string: datetime.datetime.strptime(date_string, u'%d-%m-%Y')),
                ),
            ),
        )(params.get('date'), state = ctx)
    response = requests.post(
        conf['api.urls.legislations'],
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': conf['app_name'],
            },
        data = json.dumps(dict(date = date.isoformat(), legislation = legislation.json)),
        )
    legislation_json = response.json()
    legislation.json = legislation_json.get('dated_legislation') or legislation_json.get('legislation')
    if error is not None:
        return wsgihelpers.bad_request(ctx, explanation = error)
    return templates.render(ctx, '/legislations/admin-view.mako', date = date, legislation = legislation)


@wsgihelpers.wsgify
def api1_json(req):
    ctx = contexts.Ctx(req)
    assert req.method == 'GET'
    legislation, error = conv.pipe(
        conv.input_to_slug,
        conv.not_none,
        model.Legislation.make_id_or_slug_or_words_to_instance(),
        )(req.urlvars.get('id_or_slug_or_words'), state = ctx)
    if error is not None:
        return wsgihelpers.not_found(ctx, explanation = ctx._('Legislation search error: {}').format(error))
    return wsgihelpers.respond_json(ctx, legislation.json)


@wsgihelpers.wsgify
def api1_typeahead(req):
    ctx = contexts.Ctx(req)
    headers = wsgihelpers.handle_cross_origin_resource_sharing(ctx)

    assert req.method == 'GET'
    params = req.GET
    inputs = dict(
        q = params.get('q'),
        )
    data, errors = conv.struct(
        dict(
            q = conv.base.input_to_words,
            ),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.not_found(ctx, explanation = ctx._('Legislation search error: {}').format(errors))

    criteria = {}
    if data['q'] is not None:
        criteria['words'] = {'$all': [
            re.compile(u'^{}'.format(re.escape(word)))
            for word in data['q']
            ]}
    cursor = model.Legislation.get_collection().find(criteria, ['title'])
    return wsgihelpers.respond_json(ctx,
        [
            legislation_attributes['title']
            for legislation_attributes in cursor.limit(10)
            ],
        headers = headers,
        )


def extract_legislation_inputs_from_params(ctx, params = None):
    if params is None:
        params = webob.multidict.MultiDict()
    return dict(
        datetime_begin = params.get('datetime_begin'),
        datetime_end = params.get('datetime_end'),
        description = params.get('description'),
        json = params.get('json'),
        title = params.get('title'),
        url = params.get('url'),
        )


#@wsgihelpers.wsgify
#def index(req):
#    ctx = contexts.Ctx(req)

#    assert req.method == 'GET'
#    params = req.GET
#    inputs = dict(
#        advanced_search = params.get('advanced_search'),
#        page = params.get('page'),
#        sort = params.get('sort'),
#        term = params.get('term'),
#        )
#    data, errors = conv.pipe(
#        conv.struct(
#            dict(
#                advanced_search = conv.guess_bool,
#                page = conv.pipe(
#                    conv.input_to_int,
#                    conv.test_greater_or_equal(1),
#                    conv.default(1),
#                    ),
#                sort = conv.pipe(
#                    conv.cleanup_line,
#                    conv.test_in(['slug', 'updated']),
#                    ),
#                term = conv.base.input_to_words,
#                ),
#            ),
#        conv.rename_item('page', 'page_number'),
#        )(inputs, state = ctx)
#    if errors is not None:
#        return wsgihelpers.not_found(ctx, explanation = ctx._('Legislation search error: {}').format(errors))

#    criteria = {}
#    if data['term'] is not None:
#        criteria['words'] = {'$all': [
#            re.compile(u'^{}'.format(re.escape(word)))
#            for word in data['term']
#            ]}
#    cursor = model.Legislation.find(criteria, as_class = collections.OrderedDict)
#    pager = paginations.Pager(item_count = cursor.count(), page_number = data['page_number'])
#    if data['sort'] == 'slug':
#        cursor.sort([('slug', pymongo.ASCENDING)])
#    elif data['sort'] == 'updated':
#        cursor.sort([(data['sort'], pymongo.DESCENDING), ('slug', pymongo.ASCENDING)])
#    legislations = cursor.skip(pager.first_item_index or 0).limit(pager.page_size)
#    return templates.render(ctx, '/legislations/index.mako', data = data, errors = errors, legislations = legislations,
#        inputs = inputs, pager = pager)


def route_admin(environ, start_response):
    req = webob.Request(environ)
    ctx = contexts.Ctx(req)

    legislation, error = conv.pipe(
        conv.input_to_slug,
        conv.not_none,
        model.Legislation.make_id_or_slug_or_words_to_instance(),
        )(req.urlvars.get('id_or_slug_or_words'), state = ctx)
    if error is not None:
        return wsgihelpers.not_found(ctx, explanation = ctx._('Legislation Error: {}').format(error))(
            environ, start_response)

    ctx.node = legislation

    router = urls.make_router(
        ('GET', '^/?$', admin_view),
        (('GET', 'POST'), '^/delete/?$', admin_delete),
        (('GET', 'POST'), '^/edit/?$', admin_edit),
        )
    return router(environ, start_response)


def route_admin_class(environ, start_response):
    router = urls.make_router(
        ('GET', '^/?$', admin_index),
        (('GET', 'POST'), '^/new/?$', admin_new),
        (None, '^/(?P<id_or_slug_or_words>[^/]+)(?=/|$)', route_admin),
        )
    return router(environ, start_response)


def route_api1_class(environ, start_response):
    router = urls.make_router(
        ('GET', '^/typeahead/?$', api1_typeahead),
        ('GET', '^/(?P<id_or_slug_or_words>[^/]+)/json?$', api1_json),
        )
    return router(environ, start_response)


def route_user(environ, start_response):
    router = urls.make_router(
        ('GET', '^/?$', user_index),
        ('GET', '^/(?P<id_or_slug>[^/]+)$', user_view),
        )
    return router(environ, start_response)


@wsgihelpers.wsgify
def user_index(req):
    ctx = contexts.Ctx(req)

    params = req.GET
    inputs = dict(
        advanced_search = params.get('advanced_search'),
        page = params.get('page'),
        sort = params.get('sort'),
        term = params.get('term'),
        )
    data, errors = conv.pipe(
        conv.struct(
            dict(
                advanced_search = conv.guess_bool,
                page = conv.pipe(
                    conv.input_to_int,
                    conv.test_greater_or_equal(1),
                    conv.default(1),
                    ),
                sort = conv.pipe(
                    conv.cleanup_line,
                    conv.test_in(['slug', 'updated']),
                    ),
                term = conv.base.input_to_words,
                ),
            ),
        conv.rename_item('page', 'page_number'),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.not_found(ctx, explanation = ctx._('Legislation search error: {}').format(errors))
    criteria = {}
    if data['term'] is not None:
        criteria['words'] = {'$all': [
            re.compile(u'^{}'.format(re.escape(word)))
            for word in data['term']
            ]}
    cursor = model.Legislation.find(criteria, as_class = collections.OrderedDict)
    pager = paginations.Pager(item_count = cursor.count(), page_number = data['page_number'])
    if data['sort'] == 'slug':
        cursor.sort([('slug', pymongo.ASCENDING)])
    elif data['sort'] == 'updated':
        cursor.sort([(data['sort'], pymongo.DESCENDING), ('slug', pymongo.ASCENDING)])
    legislations = cursor.skip(pager.first_item_index or 0).limit(pager.page_size)
    return templates.render(ctx, '/legislations/user-index.mako', data = data, errors = errors,
        legislations = legislations, inputs = inputs, pager = pager)


@wsgihelpers.wsgify
def user_view(req):
    ctx = contexts.Ctx(req)
    assert req.method == 'GET'
    params = req.GET
    inputs = {
        'date': params.get('date'),
        'legislation': req.urlvars.get('id_or_slug'),
        }
    data, errors = conv.struct({
        'date': conv.pipe(
            conv.cleanup_line,
            conv.function(lambda date_string: datetime.datetime.strptime(date_string, u'%d-%m-%Y')),
            conv.default(datetime.datetime.utcnow())
            ),
        'legislation': conv.pipe(
            conv.input_to_slug,
            conv.not_none,
            model.Legislation.make_id_or_slug_or_words_to_instance(),
            ),
        })(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.not_found(ctx, explanation = ctx._('Legislation search error: {}').format(errors))
    return templates.render(ctx, '/legislations/user-view.mako', date = data['date'], legislation = data['legislation'])
