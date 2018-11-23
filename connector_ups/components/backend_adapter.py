# -*- coding: utf-8 -*-
#
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
import csv
import logging
from datetime import timedelta

import MySQLdb
from odoo.addons.component.core import AbstractComponent

from odoo import fields

try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib

_logger = logging.getLogger(__name__)

recorder = {}

PACKAGE = [('retail', 'RETAIL'), ('bulk', 'BULK')]

def call_to_key(method, arguments):
    """ Used to 'freeze' the method and arguments of a call to WooCommerce
    so they can be hashable; they will be stored in a dict.

    Used in both the recorder and the tests.
    """
    def freeze(arg):
        if isinstance(arg, dict):
            items = dict((key, freeze(value)) for key, value
                         in arg.iteritems())
            return frozenset(items.iteritems())
        elif isinstance(arg, list):
            return tuple([freeze(item) for item in arg])
        else:
            return arg

    new_args = []
    for arg in arguments:
        new_args.append(freeze(arg))
    return (method, tuple(new_args))


def record(method, arguments, result):
    """ Utility function which can be used to record test data
    during synchronisations. Call it from WooCRUDAdapter._call

    Then ``output_recorder`` can be used to write the data recorded
    to a file.
    """
    recorder[call_to_key(method, arguments)] = result


def output_recorder(filename):
    import pprint
    with open(filename, 'w') as f:
        pprint.pprint(recorder, f)
    _logger.debug('recorder written to file %s', filename)


class UPSLocation(object):

    def __init__(self, server, user, passwd, db):
        self._server = server
        self.user = user
        self.passwd = passwd
        self.db = db

    @property
    def server(self):
        server = self._server
        return server


class UPS_CRUDAdapter(AbstractComponent):
    """ External Records Adapter for woo """

    _name = 'ups.crud.adapter'
    _inherit = ['base.backend.adapter']
    _usage = 'backend.adapter'

    def __init__(self, connector_env):
        """

        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(UPS_CRUDAdapter, self).__init__(connector_env)
        backend = self.backend_record
        ups = UPSLocation(
            backend.server,
            backend.user,
            backend.passwd,
            backend.db
        )
        self.ups = ups

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError

    def read(self, id, attributes=None):
        """ Returns the information of a record """
        raise NotImplementedError

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, data):
        """ Create a record on the external system """
        raise NotImplementedError

    def write(self, id, data):
        """ Update records on the external system """
        raise NotImplementedError

    def delete(self, id):
        """ Delete a record on the external system """
        raise NotImplementedError

    def _call(self, data):
        try:
            db = MySQLdb.connect(
                host=self.ups.server,
                user=self.ups.user,
                passwd=self.ups.passwd,
                db=self.ups.db,
            )
            if db:
                cr = db.cursor()

                SQL = '''INSERT INTO ups_in (
                            invoice,
                            cName,
                            name,
                            addr1,
                            addr2,
                            country,
                            city,
                            zip,
                            province,
                            phone,
                            email,
                            activeEmail,
                            transportBilling,
                            po,
                            upsAccount,
                            DelConOper,
                            DelConSigRe,
                            DecValuOp,
                            DecValAmo,
                            partNumber,
                            description,
                            quantity,
                            unitValue,
                            currency,
                            countryOfOrigin,
                            measure,
                            tariff,
                            weight,
                            L,
                            W,
                            H
                        ) VALUES ("%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s")'''
            cr.execute(SQL % (
                data.get('invoice'),
                data.get('cName'),
                data.get('name'),
                data.get('addr1'),
                data.get('addr2'),
                data.get('country'),
                data.get('city'),
                data.get('zip'),
                data.get('province'),
                data.get('phone'),
                data.get('email'),
                data.get('activeEmail'),
                data.get('transportBilling'),
                data.get('po'),
                data.get('upsAccount'),
                data.get('DelConOper'),
                data.get('DelConSigRe'),
                data.get('DecValuOp'),
                data.get('DecValAmo'),
                data.get('partNumber'),
                data.get('description'),
                data.get('quantity'),
                data.get('unitValue'),
                data.get('currency'),
                data.get('countryOfOrigin'),
                data.get('measure'),
                data.get('tariff'),
                data.get('weight'),
                data.get('L'),
                data.get('W'),
                data.get('H')
            ))
        except Exception as err:
            _logger.error(err)
            raise err


class GenericAdapter(AbstractComponent):
    _name = 'ups.adapter'
    _inherit = ['ups.crud.adapter']

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        _logger.info(u'如果调用，肯定报错。')
        return self._call('%s.search' % self._woo_model,
                          [filters] if filters else [{}])

    def read(self, id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        arguments = []
        if attributes:
            # Avoid to pass Null values in attributes. Workaround for
            # is not installed, calling info() with None in attributes
            # would return a wrong result (almost empty list of
            # attributes). The right correction is to install the
            # compatibility patch on WooCommerce.
            arguments.append(attributes)
        res = self._call(method='GET', endpoint='%s/' % self._woo_model + str(id))
        return res

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        return self._call('%s.list' % self._woo_model, [filters])

    def create(self, data):
        """ Create a record on the external system """

        res = self._call(data=data)
        return res

    def write(self, id, data):
        """ Update records on the external system """
        res = self._call(method='PUT', endpoint='%s/%s' % (self._woo_model, int(id)), data=data)
        return res

    def delete(self, id):
        """ Delete a record on the external system """
        return self._call('%s.delete' % self._woo_model, [int(id)])
