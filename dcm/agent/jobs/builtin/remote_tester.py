import json
import logging
import socket
import time
import dcm.agent.jobs as jobs


_g_logger = logging.getLogger(__name__)


class RemoteTester(jobs.Plugin):

    def __init__(self, agent, conf, job_id, items_map, name, arguments):
        super(RemoteTester, self).__init__(
            agent, conf, job_id, items_map, name, arguments)

        self._port = int(items_map['remote_port'])
        self._host = items_map['remote_host']

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self._host, self._port))

        msg = {"name": name, "arguments": arguments}

        self._msg = json.dumps(msg)

    def run(self):
        try:
            _g_logger.info("Start tester remote socket.  Send " + self._msg)
            self.sock.send(self._msg)
            _g_logger.info("waiting to get a message back")

            msg = ""
            ch = ""
            while ch != '\n':
                ch = self.sock.recv(1)
                msg = msg + ch
            _g_logger.info("Tester plugin Received " + msg)
            self.sock.close()
            rc = json.loads(msg)
            return rc
        except Exception as ex:
            _g_logger.exception("Something went wrong here")
            return {'return_code': 1}
        except:
            _g_logger.exception("Something went wrong here")
            return {'return_code': 1}

    def cancel(self, reply_rpc, *args, **kwargs):
        pass


def load_plugin(agent, conf, job_id, items_map, name, arguments):
    _g_logger.debug("IN LOAD")
    return RemoteTester(agent, conf, job_id, items_map, name, arguments)
