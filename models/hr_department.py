# -*- coding: utf-8 -*-

from odoo import models, fields, api


class inherit_hr_department(models.Model):
    _name = 'hr.department'
    _inherit = 'hr.department'

    # This is entry point to fill request_total field too
    request_resolved_catax = fields.Integer(string="Resueltas", compute="_get_resolved_request_catax", store=False)
    request_total_catax = fields.Integer(string="Solicitudes", compute="_get_total_request_catax", store=False)
    manager_photo_catax = fields.Binary(related="manager_id.image")

    def _get_resolved_request_catax(self):
        for inst in self:
            if not inst.parent_id or inst.parent_id.name == 'Tesorería':
                inst.request_resolved_catax = self.env['catax.catax'].get_resolved_requested(inst.id)

    def _get_total_request_catax(self):
        for inst in self:
            if not inst.parent_id or inst.parent_id.name == 'Tesorería':
                inst.request_total_catax = self.env['catax.catax'].get_total_requested(inst.id)
