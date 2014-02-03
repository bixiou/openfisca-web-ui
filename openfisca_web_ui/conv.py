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


"""Conversion functions"""


import collections
import datetime
from itertools import chain
import json
import re
import requests
import uuid

from biryani1.baseconv import *  # NOQA
from biryani1.bsonconv import *  # NOQA
from biryani1.datetimeconv import *  # NOQA
from biryani1.objectconv import *  # NOQA
from biryani1.jsonconv import *  # NOQA
from biryani1.states import default_state, State  # NOQA


N_ = lambda message: message
json_handler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else obj
uuid_re = re.compile(ur'[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$')


api_data_to_api_post_content = function(lambda api_data: json.dumps(api_data, default = json_handler))


def api_data_to_korma_data(api_data, state = None):
    if api_data is None:
        return None, None
    if state is None:
        state = default_state
    korma_data = {
        'familles': [],
        'declaration_impots': [],
        }
    for famille_id, famille in api_data.get('familles', {}).iteritems():
        korma_famille = {
            'personnes': [],
            }
        for role in ['parents', 'enfants']:
            for idx, personne_id in enumerate(famille.get(role, [])):
                personne_in_famille = {
                    'famille_id': famille_id,
                    'prenom_condition': dict(api_data.get('individus', {}).iteritems()),
                    'role': role,
                    }
                personne_in_famille['prenom_condition']['prenom'] = famille[role][idx]
                korma_famille['personnes'].append({'personne_in_famille': personne_in_famille})
        korma_data['familles'].append(korma_famille)

    for declaration_impot_id, declaration_impot in api_data.get('foyers_fiscaux', {}).iteritems():
        korma_declaration_import = {
            'personnes': [],
            }
        for role in ['declarants', 'personne_a_charges']:
            for idx, personne_id in enumerate(declaration_impot.get(role, [])):
                personne_in_declaration_impots = {
                    'declaration_impot_id': declaration_impot_id,
                    'prenom_condition': dict(api_data.get('individus', {}).iteritems()),
                    'role': role,
                    }
                personne_in_declaration_impots['prenom_condition']['prenom'] = declaration_impot[role][idx]
                korma_declaration_import['personnes'].append(
                    {'personne_in_declaration_impots': personne_in_declaration_impots}
                    )
        korma_data['declaration_impots'].append(korma_declaration_import)
    return korma_data, None


def api_post_content_to_simulation_output(api_post_content, state = None):
    from . import conf
    if api_post_content is None:
        return None, None
    if state is None:
        state = default_state
    try:
        response = requests.post(
            conf['api.url'],
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': conf['app_name'],
                },
            data = api_post_content,
            )
    except requests.exceptions.ConnectionError:
        return api_post_content, state._('Unable to connect to API, url: {}').format(conf['api.url'])
    if not response.ok:
        return api_post_content, response.json(object_pairs_hook = collections.OrderedDict).get('error')
    simulation_output = response.json(object_pairs_hook = collections.OrderedDict)
    return simulation_output, None


api_data_to_simulation_output = pipe(api_data_to_api_post_content, api_post_content_to_simulation_output)


date_to_datetime = function(lambda value: datetime.datetime(*(value.timetuple()[:6])))


datetime_to_date = function(lambda value: value.date())


declaration_impot_korma_data_to_declaration_impots = pipe(
    function(lambda item: item.get('declaration_impots')),
    uniform_sequence(
        pipe(
            function(lambda item: item.get('personnes')),
            uniform_sequence(
                pipe(
                    function(lambda item: item.get('personne_in_declaration_impots')),
                    struct(
                        {
                            'declaration_impot_id': cleanup_line,
                            'role': test_in([u'declarants', u'personne_a_charges']),
                            'prenom_condition': noop,
                            },
                        default = noop,
                        ),
                    rename_item('prenom_condition', 'personne'),
                    rename_item('declaration_impot_id', 'id'),
                    ),
                ),
            ),
        ),
    function(lambda lists: list(chain.from_iterable(lists))),
    )


declaration_impot_korma_data_to_personnes = pipe(
    function(lambda item: item.get('declaration_impots')),
    uniform_sequence(
        pipe(
            function(lambda item: item.get('personnes')),
            uniform_sequence(
                pipe(
                    function(lambda item: item.get('personne_in_declaration_impots', {}).get('prenom_condition')),
                    rename_item('prenom', 'id'),
                    ),
                ),
            ),
        ),
    function(lambda lists: list(chain.from_iterable(lists))),
    )


famille_korma_data_to_familles = pipe(
    function(lambda item: item.get('familles')),
    uniform_sequence(
        pipe(
            function(lambda item: item.get('personnes')),
            uniform_sequence(
                pipe(
                    function(lambda item: item.get('personne_in_famille')),
                    struct(
                        {
                            'famille_id': cleanup_line,
                            'role': test_in(['parents', 'enfants']),
                            'prenom_condition': noop,
                            },
                        default = noop,
                        ),
                    rename_item('prenom_condition', 'personne'),
                    rename_item('famille_id', 'id'),
                    ),
                ),
            ),
        ),
    function(lambda lists: list(chain.from_iterable(lists))),
    )


famille_korma_data_to_personnes = pipe(
    function(lambda item: item.get('familles')),
    uniform_sequence(
        pipe(
            function(lambda item: item.get('personnes')),
            uniform_sequence(
                pipe(
                    function(lambda item: item.get('personne_in_famille', {}).get('prenom_condition')),
                    rename_item('prenom', 'id'),
                    ),
                ),
            ),
        ),
    function(lambda lists: list(chain.from_iterable(lists))),
    )


input_to_uuid = pipe(
    cleanup_line,
    test(uuid_re.match, error = N_(u'Invalid UUID format')),
    )


input_to_words = pipe(
    input_to_slug,
    function(lambda slug: sorted(set(slug.split(u'-')))),
    empty_to_none,
    )


menage_korma_data_to_menages = pipe(
    function(lambda item: item.get('logements_principaux')),
    uniform_sequence(
        pipe(
            function(lambda item: item.get('logement_principal')),
            struct(
                {
                    'localite': cleanup_line,
                    'logement_principal_id': cleanup_line,
                    'loyer': noop,
                    'personnes': uniform_sequence(
                        pipe(
                            function(lambda item: item.get('personne_in_logement_principal', {}).get('prenom_condition')),
                            rename_item('prenom', 'id'),
                            ),
                        ),
                    'so': cleanup_line,
                    },
                default = noop,
                ),
            rename_item('logement_principal_id', 'id'),
            ),
        ),
    )


menage_korma_data_to_personnes = pipe(
    function(lambda item: item.get('logements_principaux')),
    uniform_sequence(
        pipe(
            function(lambda item: item.get('logement_principal')),
            function(lambda item: item.get('personnes')),
            uniform_sequence(
                pipe(
                    function(lambda item: item.get('personne_in_logement_principal', {}).get('prenom_condition')),
                    rename_item('prenom', 'id'),
                    ),
                ),
            ),
        ),
    function(lambda lists: list(chain.from_iterable(lists))),
    )


def method(method_name, *args, **kwargs):
    def method_converter(value, state = None):
        if value is None:
            return value, None
        return getattr(value, method_name)(state or default_state, *args, **kwargs)
    return method_converter


def korma_to_api(korma_data, state = None):
    if korma_data is None:
        return None, None
    if state is None:
        state = default_state
    new_person_id = None
    new_famille_id = None
    new_foyer_fiscal_id = None
    new_logement_principal_id = None


    api_data = state.session.user.api_data or {}
    for korma_personne in korma_data['personnes']:
        if korma_personne['id'] == 'new':
            new_person_id = unicode(uuid.uuid4()).replace('-', '')
            api_data.setdefault('individus', {})[new_person_id] = korma_personne[korma_personne['id']]
        else:
            api_data.setdefault('individus', {})[korma_personne['id']].update(korma_personne[korma_personne['id']])

    if korma_data.get('familles'):
        for korma_famille in korma_data['familles']:
            if korma_famille['id'] is None and new_famille_id is None:
                new_famille_id = unicode(uuid.uuid4()).replace('-', '')
            personnes = set(
                api_data.setdefault('familles', {}).get(korma_famille['id'] or new_famille_id, {}).get(
                    korma_famille['role'], [])
                )
            personnes.add(
                korma_famille['personne']['prenom'] if korma_famille['personne']['prenom'] != 'new' else new_person_id
                )
            api_data.setdefault('familles', {}).setdefault(
                korma_famille['id'] or new_famille_id, {})[korma_famille['role']] = list(personnes)

    if korma_data.get('declaration_impots'):
        for korma_foyer_fiscal in korma_data['declaration_impots']:
            if korma_foyer_fiscal['id'] is None and new_foyer_fiscal_id is None:
                new_foyer_fiscal_id = unicode(uuid.uuid4()).replace('-', '')
            personnes = set(
                api_data.setdefault('foyers_fiscaux', {}).get(
                    korma_foyer_fiscal['id'] or new_foyer_fiscal_id, {}).get(
                        korma_foyer_fiscal['role'], []
                        )
                )
            personnes.add(
                korma_foyer_fiscal['personne']['prenom'] if korma_foyer_fiscal['personne']['prenom'] != 'new' else new_person_id
                )
            api_data.setdefault('foyers_fiscaux', {}).setdefault(
                korma_foyer_fiscal['id'] or new_foyer_fiscal_id, {})[korma_foyer_fiscal['role']] = list(personnes)

    if korma_data.get('logement_principal'):
        for korma_logement_principal in korma_data['logement_principal']:
            if korma_logement_principal['id'] is None and new_logement_principal_id is None:
                new_logement_principal_id = unicode(uuid.uuid4()).replace('-', '')
            personnes = set(
                api_data.setdefault('menages', {}).get(
                    korma_logement_principal['id'] or new_logement_principal_id, {}).get('occupants', [])
                )
            for personne in korma_logement_principal['personnes']:
                personnes.add(personne['id'] if personne['id'] != 'new' else new_person_id)
            api_data.setdefault('menages', {}).setdefault(
                korma_logement_principal['id'] or new_logement_principal_id, {})['occupants'] = list(personnes)
    return api_data, None


def user_data_to_api_data(user_data, state = None):
    if user_data is None:
        return None, None
    if state is None:
        state = default_state

    api_data = {
        'familles': user_data.get('familles', {}).values(),
        'foyers_fiscaux': user_data.get('foyers_fiscaux', {}).values(),
        'menages': user_data.get('menages', {}).values(),
        'individus': [],
        }
    for individu_id in user_data.get('individus', {}).iterkeys():
        individu = dict(
            (key, value)
            for key, value in user_data['individus'][individu_id].iteritems()
            )
        individu['id'] = individu_id
        api_data['individus'].append(individu)
    return {'scenarios': [api_data]}, None
