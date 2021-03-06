#
#  Copyright (C) 2014 Dell, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import hashlib
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.api.exceptions as plugin_exceptions
import dcm.agent.plugins.api.utils as plugin_utils


_g_logger = logging.getLogger(__name__)


class FetchRunScript(plugin_base.Plugin):

    protocol_arguments = {
        "url": ("The location of the script as a url", True, str, None),
        "connect_timeout": ("The number of seconds to wait to establish a "
                            "connection to the soure url", False, int, 30),
        "checksum": ("The sha256 checksum of the script.", False, str, None),
        "inpython": ("Run the downloaded script with the current python "
                     "environment.",
                     False, bool, False),
        "runUnderSudo": ("Run this script as the root use with sudo.",
                         False, bool, False),
        "arguments": ("The list of arguments to be passed to the "
                      "downloaded script",
                      False, list, None),
        "ssl_cert": ("The expected cert for the source of the executable "
                     "script to be downloaded.", False,
                     str, None),
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(FetchRunScript, self).__init__(
            conf, job_id, items_map, name, arguments)

    def _do_http_download(self):
        exe_file = self.conf.get_temp_file("fetch_exe_file")
        timeout = self.args.connect_timeout

        u_req = urllib.request.Request(self.args.url)
        u_req.add_header("Content-Type", "application/x-www-form-urlencoded")
        u_req.add_header("Connection", "Keep-Alive")
        u_req.add_header("Cache-Control", "no-cache")

        response = urllib.request.urlopen(u_req, timeout=timeout)
        if response.code != 200:
            raise plugin_exceptions.AgentPluginParameterBadValueException(
                self.name,
                "url",
                expected_values="The url %s was invalid" % self.args.url)

        sha256 = hashlib.sha256()
        data = response.read(1024)
        with open(exe_file, "wb") as fptr:
            while data:
                sha256.update(data)
                fptr.write(data)
                data = response.read(1024)
        actual_checksum = sha256.hexdigest()
        if self.args.checksum and actual_checksum != self.args.checksum:
            raise plugin_exceptions.AgentPluginOperationException(
                "The checksum did not match")
        return exe_file, True

    def _do_file(self):
        url_parts = urllib.parse.urlparse(self.args.url)
        return url_parts.path, False

    def run(self):
        _scheme_map = {'http': self._do_http_download,
                       'https': self._do_http_download,
                       'file': self._do_file}

        url_parts = urllib.parse.urlparse(self.args.url)

        if url_parts.scheme not in list(_scheme_map.keys()):
            # for now we are only accepting http.  in the future we will
            # switch on scheme to decide what cloud storage protocol module
            # to use
            raise plugin_exceptions.AgentPluginParameterBadValueException(
                "url", url_parts.scheme,
                expected_values=str(list(_scheme_map.keys())))

        func = _scheme_map[url_parts.scheme]
        try:
            exe_file, cleanup = func()
        except BaseException as ex:
            if type(ex) == plugin_exceptions.AgentPluginOperationException:
                raise
            return plugin_base.PluginReply(
                1, error_message="Failed to download the URL %s: %s"
                                 % (self.args.url, str(ex)))

        try:
            os.chmod(exe_file, 0o755)

            command_list = []
            if self.args.runUnderSudo:
                command_list.append(self.conf.system_sudo)
            if self.args.inpython:
                command_list.append(sys.executable)
            command_list.append(exe_file)

            if self.args.arguments:
                command_list.extend(self.args.arguments)
            _g_logger.debug("FetchRunScript is running the command %s"
                            % str(command_list))
            (stdout, stderr, rc) = plugin_utils.run_command(
                self.conf, command_list)
            _g_logger.debug("Command %s: stdout %s.  stderr: %s" %
                            (str(command_list), stdout, stderr))
            return plugin_base.PluginReply(
                rc, message=stdout, error_message=stderr, reply_type="void")
        finally:
            if exe_file and cleanup and os.path.exists(exe_file):
                os.remove(exe_file)


def load_plugin(conf, job_id, items_map, name, arguments):
    return FetchRunScript(conf, job_id, items_map, name, arguments)
