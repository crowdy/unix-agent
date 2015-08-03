import logging
import sys
import threading

import dcm.agent.events.globals as events
import dcm.agent.logger as dcm_logger
import dcm.agent.utils as utils
import dcm.agent.plugins.api.base as plugin_base
import dcm.agent.plugins.builtin.remove_user as remove_user


_g_logger = logging.getLogger(__name__)


class CleanImage(plugin_base.Plugin):
    protocol_arguments = {
        "delUser":
            ("List of accounts to remove",
             False, list, None),
        "delKeys":
            ("Flag to delete private keys in users home directories",
             False, bool, False)
    }

    def __init__(self, conf, job_id, items_map, name, arguments):
        super(CleanImage, self).__init__(
            conf, job_id, items_map, name, arguments)
        self._done_event = threading.Event()
        self._topic_error = None

    def delete_private_keys(self):
        exe = self.conf.get_script_location("delete_keys.py")
        cmd = [
            self.conf.system_sudo,
            '-E',
            sys.executable,
            exe
        ]

        (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
        if rc != 0:
            return plugin_base.PluginReply(
                rc, messge=stdout, error_message=stderr)
        return plugin_base.PluginReply(
            0, message="Keys were deleted successfully")

    def delete_history(self):
        exe = self.conf.get_script_location("delete_history.py")
        cmd = [
            self.conf.system_sudo,
            '-E',
            sys.executable,
            exe
        ]

        (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
        if rc != 0:
            return plugin_base.PluginReply(
                rc, messge=stdout, error_message=stderr)
        return plugin_base.PluginReply(
            0, message="History deleted successfully")

    def general_cleanup(self, dbfile):
        exe = self.conf.get_script_location("general_cleanup.py")
        cmd = [
            self.conf.system_sudo,
            '-E',
            sys.executable,
            exe,
            dbfile
        ]

        (stdout, stderr, rc) = utils.run_command(self.conf, cmd)
        if rc != 0:
            return plugin_base.PluginReply(
                rc, messge=stdout, error_message=stderr)
        return plugin_base.PluginReply(
            0, message="General cleanup completed successfully")

    def _clean_topic_done(self, topic_error):
        self._topic_error = topic_error
        self._done_event.set()

    def run(self):
        message = ''
        try:
            events.global_pubsub.publish(
                events.DCMAgentTopics.CLEANUP,
                topic_kwargs={'request_id': self.job_id},
                done_cb=self._clean_topic_done)

            if self.args.delUser:
                dcm_logger.log_to_dcm_console_job_details(
                    job_name=self.name,
                    details='Deleting users.')
                for user in self.args.delUser:
                    rdoc = remove_user.RemoveUser(
                        self.conf,
                        self.job_id,
                        {'script_name': 'removeUser'},
                         'remove_user',
                         {'userId': user}).run()
                    if rdoc.get_return_code() != 0:
                        rdoc.set_message(rdoc.get_message() +
                                         " : Delete users failed on %s" % user)
                        return rdoc

            if self.args.delKeys:
                dcm_logger.log_to_dcm_console_job_details(
                    job_name=self.name, details='Deleting private keys.')
                res_doc = self.delete_private_keys()
                if res_doc.get_return_code() != 0:
                    return res_doc

            dcm_logger.log_to_dcm_console_job_details(
                job_name=self.name, details='Deleting history files.')
            res_doc = self.delete_history()
            if res_doc.get_return_code() != 0:
                return res_doc

            dcm_logger.log_to_dcm_console_job_details(
                job_name=self.name, details='Starting general cleanup.')
            res_doc = self.general_cleanup(self.conf.storage_dbfile)
            if res_doc.get_return_code() != 0:
                return res_doc

            self._done_event.wait()
            if self._topic_error is not None:
                return plugin_base.PluginReply(
                    1, error_message=str(self._topic_error))

            return plugin_base.PluginReply(
                0, message="Clean image command ran successfully")
        except Exception as ex:
            _g_logger.exception("clean_image failed: " + str(ex))
            return plugin_base.PluginReply(
                1, message=str(ex), error_message=str(ex))


def load_plugin(conf, job_id, items_map, name, arguments):
    return CleanImage(conf, job_id, items_map, name, arguments)