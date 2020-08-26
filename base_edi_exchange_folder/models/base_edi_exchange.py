# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.modules.module import get_resource_path, get_module_path
from datetime import datetime, timedelta
import logging
import os
import glob

_logger = logging.getLogger(__name__)


class BaseEDIExchange(models.Model):
    _inherit = 'base.edi.exchange'

    type = fields.Selection(selection_add=[('folder', _('Folder'))])

    send_folder = fields.Char(string="Folder to Send")
    receive_folder = fields.Char(string="Folder to Receive")

    @api.onchange('type')
    def onchange_type(self):
        super(BaseEDIExchange, self).onchange_type()
        if self.type == 'folder':
            path = os.path.dirname(
                os.path.split(os.path.realpath(__file__))[0])
            if not self.send_folder:
                self.send_folder = os.path.join(path, 'send_folder')
            if not self.receive_folder:
                self.receive_folder = os.path.join(path, 'receive_folder')

    @api.multi
    def send(self, file, vals=None):
        _logger.debug('Base Send folder called.')
        if not vals:
            vals = {}
        if self.type != 'folder':
            return super(BaseEDIExchange, self).send()
        message_id = vals.get("conversation_id")
        vals.update({
            'name': message_id,
            'message_id': message_id,
            'original_filename': message_id + ".pdf",
            'file_content': file,
            'state': 'pending',
            'edi_exchange_id': self.id,
            'direction': 'outbound',
        })
        file_transfer = self.env['base.edi.transfer'].create(vals)
        if not os.path.exists(self.send_folder):
            os.mkdir(self.send_folder)
        complete_path = os.path.join(self.send_folder, message_id + ".pdf")
        with open(complete_path, 'wb+') as f:
            f.write(file)
        file_transfer.state = 'sent'
        file_transfer.read_date = datetime.now()
        return True

    @api.multi
    def receive(self):
        _logger.debug('Base Receive folder called.')
        if self.type != 'folder':
            return super(BaseEDIExchange, self).receive()
        files = os.listdir(self.receive_folder)
        for file in files:
            complete_path = os.path.join(self.receive_folder, file)
            # check if file was read and processed before
            file_transfer = self.env['base.edi.transfer'].get_transfer(file)
            current_file_ts = datetime.utcfromtimestamp(os.path.getmtime(complete_path)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            # no file transfer - create new one
            with open(complete_path, 'rb') as file_to_process:
                file_content = file_to_process.read()
                transfer_vals = {
                    'name': file,
                    'original_filename': file + ".pdf",
                    'file_content': file_content,
                    'state': 'pending',
                    # 'ref': reference,
                    'edi_exchange_id': self.id,
                    'direction': 'inbound',
                    'file_timestamp': datetime.utcfromtimestamp(os.path.getmtime(complete_path)),
                    'read_date': datetime.now(),
                }
            if not file_transfer:
                file_transfer = self.env['base.edi.transfer'].create(transfer_vals)
                try:
                    received_from_import = file_transfer.identify_and_import_object()
                except Exception as e:
                    file_transfer.state = "error"
                    file_transfer.error_text = str(e)
            else:
                if file_transfer.file_timestamp == current_file_ts:
                    continue
                file_transfer.write(transfer_vals)
                try:
                    received_from_update = file_transfer.identify_and_update_object()
                except Exception as e:
                    file_transfer.state = "error"
                    file_transfer.error_text = str(e)
            file_transfer.state = "processed"
        return True
