from collections import namedtuple
import unittest

import dcm.agent.plugins.loader as plugin_loader

class TestHandshake(unittest.TestCase):

    def test_mount_volume_supported(self):
        FakeConf = namedtuple('FakeConf', 'cloud_type platform_name')
        conf = FakeConf('Amazon', 'ubuntu')
        module = 'dcm.agent.plugins.builtin.mount_volume'
        items_map = {'type': 'python_module',
                     'module_name': module}
        features = plugin_loader.get_module_features(
            conf, 'mount_volume', items_map)
        self.assertIn('mount', features)
        self.assertIn('format', features)

    def test_mount_volume_unsupported_cloud(self):
        FakeConf = namedtuple('FakeConf', 'cloud_type platform_name')
        conf = FakeConf('NotACloud', 'ubuntu')
        module = 'dcm.agent.plugins.builtin.mount_volume'
        items_map = {'type': 'python_module',
                     'module_name': module}
        features = plugin_loader.get_module_features(
            conf, 'mount_volume', items_map)
        self.assertFalse(features)

    def test_mount_volume_unsupported_platform(self):
        FakeConf = namedtuple('FakeConf', 'cloud_type platform_name')
        conf = FakeConf('Amazon', 'NotReal')
        module = 'dcm.agent.plugins.builtin.mount_volume'
        items_map = {'type': 'python_module',
                     'module_name': module}
        features = plugin_loader.get_module_features(
            conf, 'mount_volume', items_map)
        self.assertFalse(features)

    def test_mount_volume_unsupported_everything(self):
        FakeConf = namedtuple('FakeConf', 'cloud_type platform_name')
        conf = FakeConf('NotACloud', 'NotReal')
        module = 'dcm.agent.plugins.builtin.mount_volume'
        items_map = {'type': 'python_module',
                     'module_name': module}
        features = plugin_loader.get_module_features(
            conf, 'mount_volume', items_map)
        self.assertFalse(features)
