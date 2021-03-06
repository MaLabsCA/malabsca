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

import logging
import platform
from datetime import datetime

from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector.exception import IDMissingInBackend

from odoo import fields, _

_logger = logging.getLogger(__name__)


class MalabsImporter(AbstractComponent):
    """ Base importer for MalabsCommerce """

    _name = 'malabs.importer'
    _inherit = ['base.importer']
    _usage = 'record.importer'

    def __init__(self, connector_env):
        """
        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(MalabsImporter, self).__init__(connector_env)
        self.malabs_id = None
        self.malabs_record = None

    # def _get_malabs_data(self):
    #     """ Return the raw MalabsCommerce data for ``self.malabs_id`` """
    #     return self.backend_adapter.read(self.malabs_id)

    def _before_import(self):
        """ Hook called before the import, when we have the MalabsCommerce
        data"""

    def _is_uptodate(self, binding):
        """Return True if the import should be skipped because
        it is already up-to-date in OpenERP"""
        WOO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
        dt_fmt = WOO_DATETIME_FORMAT
        assert self.malabs_record
        if not self.malabs_record:
            return  # no update date on MalabsCommerce, always import it.
        if not binding:
            return  # it does not exist so it should not be skipped
        sync = binding.sync_date
        if not sync:
            return
        from_string = fields.Datetime.from_string
        sync_date = from_string(sync)
        self.malabs_record['updated_at'] = {}
        self.malabs_record['updated_at'] = {'to': datetime.now().strftime(dt_fmt)}
        malabs_date = from_string(self.malabs_record['updated_at']['to'])
        # if the last synchronization date is greater than the last
        # update in malabs, we skip the import.
        # Important: at the beginning of the exporters flows, we have to
        # check if the malabs_date is more recent than the sync_date
        # and if so, schedule a new import. If we don't do that, we'll
        # miss changes done in MalabsCommerce
        return malabs_date < sync_date

    def _import_dependency(self, malabs_id, binding_model,
                           importer_class=None, always=False):
        """ Import a dependency.

        The importer class is a class or subclass of
        :class:`MalabsImporter`. A specific class can be defined.

        :param malabs_id: id of the related binding to import
        :param binding_model: name of the binding model for the relation
        :type binding_model: str | unicode
        :param importer_cls: :class:`openerp.addons.connector.\
                                     connector.ConnectorUnit`
                             class or parent class to use for the export.
                             By default: MalabsImporter
        :type importer_cls: :class:`openerp.addons.connector.\
                                    connector.MetaConnectorUnit`
        :param always: if True, the record is updated even if it already
                       exists, note that it is still skipped if it has
                       not been modified on MalabsCommerce since the last
                       update. When False, it will import it only when
                       it does not yet exist.
        :type always: boolean
        """
        if not malabs_id:
            return
        if importer_class is None:
            importer_class = self._usage
        binder = self.binder_for(binding_model)
        if always or binder.to_openerp(malabs_id) is None:
            importer = self.component(usage=importer_class, model_name=binding_model)
            importer.run(malabs_id)

    def _import_dependencies(self):
        """ Import the dependencies for the record

        Import of dependencies can be done manually or by calling
        :meth:`_import_dependency` for each dependency.
        """
        return

    def _map_data(self):
        """ Returns an instance of
        :py:class:`~openerp.addons.connector.components.mapper.MapRecord`

        """
        return self.mapper.map_record(self.malabs_record)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid.

        Raise `InvalidDataError`
        """
        return

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        return

    def _get_binding(self):
        return self.binder.to_openerp(self.malabs_id, browse=True)

    def _create_data(self, map_record, **kwargs):
        return map_record.values(for_create=True, **kwargs)

    def _create(self, data):
        """ Create the OpenERP record """
        # special check on data before import
        self._validate_data(data)
        model = self.model.with_context(connector_no_export=True)
        model = str(model).split('()')[0]
        binding = self.env[model].create(data)
        _logger.debug('%d created from malabs %s', binding, self.malabs_id)
        return binding

    def _update_data(self, map_record, **kwargs):
        return map_record.values(**kwargs)

    def _update(self, binding, data):
        """ Update an OpenERP record """
        # special check on data before import
        self._validate_data(data)
        binding.with_context(connector_no_export=True).write(data)
        _logger.debug('%d updated from malabs %s', binding, self.malabs_id)
        return

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        return

    def run(self, malabs_record, force=False):
        """ Run the synchronization

        :param malabs_id: identifier of the record on MalabsCommerce
        """
        self.malabs_id = malabs_record.get('barcode', None)
        self.malabs_record = malabs_record

        skip = self._must_skip()
        if skip:
            return skip

        binding = self._get_binding()
        if not force and self._is_uptodate(binding):
            return _('Already up-to-date.')
        self._before_import()

        # import the missing linked resources
        self._import_dependencies()

        map_record = self._map_data()

        if binding:
            record = self._update_data(map_record)
            self._update(binding, record)
        else:
            record = self._create_data(map_record)
            binding = self._create(record)
            self.binder.bind(self.malabs_id, binding)

        self._after_import(binding)


class BatchImporter(AbstractComponent):

    """ The role of a BatchImporter is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """
    
    _name = 'malabs.batch.importer'
    _usage = 'batch.importer'
    _inherit = ['base.importer']


    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        records = self.backend_adapter.read(
            filters,
            from_date=from_date,
            to_date=to_date,
        )

        for record in records:
            self._import_record(record, priority=30)

    def _import_record(self, record_id):
        """ Import a record directly or delay the import of the record.

        Method to implement in sub-classes.
        """
        raise NotImplementedError


class DelayedBatchImporter(AbstractComponent):

    """ Delay import of the records """
    _inherit = 'malabs.batch.importer'
    _name = 'malabs.delayed.batch.importer'

    def _import_record(self, record, **kwargs):
        """ Delay the import of the records"""
        # if platform.system() == 'Linux':
        #     self.model.with_delay().import_record(self.backend_record, record)
        # else:
        #     self.model.import_record(self.backend_record, record)
        self.model.import_record(self.backend_record, record)