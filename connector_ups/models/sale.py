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

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

from odoo import models, fields

_logger = logging.getLogger(__name__)


class UPSSaleOrder(models.Model):
    _name = 'ups.sale.order.line'
    _inherit = 'ups.binding'
    _inherits = {'sale.order.line': 'odoo_id'}
    _description = 'UPS Sale Order'

    odoo_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Sale Order Line',
        required=True,
        ondelete='cascade'
    )

    backend_id = fields.Many2one(
        comodel_name='ups.backend',
        string='Malabs Backend',
        store=True,
        readonly=False,
    )


class SaleOrderAdapter(Component):
    _inherit = ['ups.adapter']
    _name = 'ups.sale.order.adapter'
    _apply_on = 'ups.sale.order.line'

    def search(self, filters=None, from_date=None, to_date=None):
        """ Search records according to some criteria and return a
        list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}
        WOO_DATETIME_FORMAT = '%Y/%m/%d %H:%M:%S'
        dt_fmt = WOO_DATETIME_FORMAT
        if from_date is not None:
            filters.setdefault('updated_at', {})
            filters['updated_at']['from'] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters.setdefault('updated_at', {})
            filters['updated_at']['to'] = to_date.strftime(dt_fmt)

        ids = []
        res = self._call(method='GET', endpoint=self._woo_model)
        for picking in res:
            ids += [picking.get('id')]
        return ids


class SaleOrderLineBatchExporter(Component):
    """ Export the Odoo Sale Order Line.
    """
    _inherit = ['ups.delayed.batch.exporter']
    _name = 'ups.sale.order.batch.exporter'
    _apply_on = ['ups.sale.order.line']


class SaleOrderLineExporter(Component):
    _apply_on = ['ups.sale.order.line']
    _name = 'ups.sale.order.exporter'
    _inherit = ['ups.exporter']


class SaleOrderExportMapper(Component):
    _apply_on = 'ups.sale.order.line'
    _name = 'ups.sale.order.export.mapper'
    _inherit = ['base.export.mapper']

    @mapping
    def fields(self, rec):
        record = {
            'odoo_id': rec.id,
            'cName': rec.order_id.partner_shipping_id.company_id.name,
            'name': rec.order_id.partner_shipping_id.contact_name if rec.order_id.partner_shipping_id.contact_name else '',
            'addr1': rec.order_id.partner_shipping_id.street,
            'addr2': rec.order_id.partner_shipping_id.street2 if rec.order_id.partner_shipping_id.street2 else '',
            'country': rec.order_id.partner_shipping_id.country_id.code,
            'city': rec.order_id.partner_shipping_id.city,
            'zip': rec.order_id.partner_shipping_id.zip,
            'province': rec.order_id.partner_shipping_id.state_id.code,
            'phone': rec.order_id.partner_shipping_id.phone,
            'email': rec.order_id.partner_shipping_id.email,
            'activeEmail': 'N',
            'transportBilling': 'SHP',
            'upsAccount': rec.order_id.ups_account if rec.order_id.ups_account else '',
            'DelConOper': rec.order_id.delivery_confirmation_option.upper() if rec.order_id.delivery_confirmation_option else '',
            'DelConSigRe': rec.order_id.delivery_confirmation_signature_required.upper() if rec.order_id.delivery_confirmation_signature_required else '',
            'DecValuOp': rec.order_id.declared_value_option.upper if rec.order_id.declared_value_option else '',
            'DecValAmo': rec.order_id.declared_value_amount if rec.order_id.declared_value_amount else '',
            'partNumber': rec.product_id.item if rec.product_id.item else '',
            'description': rec.product_id.name,
            'quantity': rec.product_uom_qty,
            'unitValue': rec.price_unit,
            'currency': rec.currency_id.name,
            'countryOfOrigin': rec.order_id.partner_shipping_id.country_id.code,
            'measure': 'EA',
            'tariff': 'ComCode',
            'weight': rec.product_id.weight if rec.product_id.weight else 0,
            'L': rec.product_id.length_cm if rec.product_id.length_cm else 0,
            'W': rec.product_id.width_cm if rec.product_id.width_cm else 0,
            'H': rec.product_id.height_cm if rec.product_id.height_cm else 0,
        }

        invoices = rec.env['account.invoice'].search([('id', 'in', rec.order_id.invoice_ids.ids)])
        if invoices:
            record.update(
                {'invoice': invoices[0].sequence_number_next_prefix + invoices[0].sequence_number_next}
            )

        if rec.order_id.purchase_order:
            record.update({'po': rec.order_id.purchase_order.name})

        return record
