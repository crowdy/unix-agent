#  ========= CONFIDENTIAL =========
#
#  Copyright (C) 2010-2014 Dell, Inc. - ALL RIGHTS RESERVED
#
#  ======================================================================
#   NOTICE: All information contained herein is, and remains the property
#   of Dell, Inc. The intellectual and technical concepts contained herein
#   are proprietary to Dell, Inc. and may be covered by U.S. and Foreign
#   Patents, patents in process, and are protected by trade secret or
#   copyright law. Dissemination of this information or reproduction of
#   this material is strictly forbidden unless prior written permission
#   is obtained from Dell, Inc.
#  ======================================================================
import logging

import dcm.agent.plugins.api.base as plugin_base
import dcmdocker.utils as docker_utils


_g_logger = logging.getLogger(__name__)


class RestartContainer(docker_utils.DockerJob):

    protocol_arguments = {
        "container": ("", True, str, None),
        "timeout": ("", False, int, 10),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(RestartContainer, self).__init__(
            conf, job_id, items_map, name, arguments)

    def run(self):
        self.docker_conn.restart(self.args.container,
                                 self.args.timeout)
        return plugin_base.PluginReply(0, reply_type="void")


def load_plugin(conf, job_id, items_map, name, arguments):
    return RestartContainer(conf, job_id, items_map, name, arguments)
