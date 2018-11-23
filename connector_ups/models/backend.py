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
import platform

from odoo import models, api, fields, _


class UPS_Backend(models.Model):
    _name = 'ups.backend'
    _inherit = 'connector.backend'
    _description = 'UPS Backend Configuration'

    server = fields.Char(string='MySQL Server', required=True)
    user = fields.Char(string='User', required=True)
    passwd = fields.Char(string='Pass Word', required=True)
    db = fields.Char(string='MySQL Database', required=True)

    def export_data(self, ups_model, filter=None):
        if platform.system() == 'Linux':
            self.env[ups_model].with_delay().export_batch(self, filter)
        else:
            self.env[ups_model].export_batch(self, filter)
        return True

    @api.multi
    def export_picking(self):
        self.ensure_one()
        filter = (
            ('order_id.state', '=', 'sale'),
            ('order_id.carrier_id', 'in', self.env['delivery.carrier'].search([('delivery_type', '=', 'ups'),]).ids)
        )
        return self.export_data('ups.sale.order.line', filter)
