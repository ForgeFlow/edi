# Copyright 2021 ForgeFlow S.L. (https://www.forgeflow.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class EDIStorageReceiveComponent(Component):

    _name = "edi.storage.component.receive"
    _inherit = [
        "edi.component.receive.mixin",
        "edi.storage.component.mixin",
    ]
    _usage = "storage.receive"

    def receive(self):
        checker = self.component(usage="storage.check")
        result = checker.check()
        _logger.info("LOIS TEST - checker")
        if not result:
            # all good here
            _logger.info("LOIS TEST - checker 2")
            return True

        direction = self.exchange_record.direction
        filename = self.exchange_record.exchange_filename
        path = self._remote_file_path(direction, "pending", filename)
        _logger.info("LOIS TEST - path: %s" % path)
        filedata = self.storage.get(path.as_posix())
        _logger.info("LOIS TEST - filedata: %s" % filedata)
        return filedata
