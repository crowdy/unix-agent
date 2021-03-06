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
import datetime
import json
import threading

import dcm.agent.exceptions as exceptions
import dcm.agent.utils as utils

from dcm.agent.events.globals import global_space as dcm_events


class BasePage(object):
    def __init__(self, page_size):
        self.creation_time = datetime.datetime.now()
        self._page_size = page_size
        self._lock = threading.RLock()

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()


class JsonPage(BasePage):
    def __init__(self, page_size, obj_list):
        super(JsonPage, self).__init__(page_size)
        self._obj_list = obj_list

    @utils.class_method_sync
    def get_next_page(self):
        page_list = []
        size_so_far = 0
        for json_obj in self._obj_list:
            line_size = len(json.dumps(json_obj))
            if size_so_far + line_size > self._page_size:
                break
            page_list.append(json_obj)
            size_so_far += line_size
        self._obj_list = self._obj_list[len(page_list):]
        return (page_list, len(self._obj_list))


class StringPage(BasePage):
    def __init__(self, page_size, string_data):
        super(StringPage, self).__init__(page_size)
        self._string_data = string_data

    @utils.class_method_sync
    def get_next_page(self):
        this_page = self._string_data[:self._page_size]
        self._string_data = self._string_data[self._page_size:]
        return (this_page, len(self._string_data))


class PageMonitor(object):

    def __init__(self, page_size=12*1024, life_span=60*60*2, sweep_time=10):
        self._pages = {}
        self._page_size = page_size
        self._lock = threading.RLock()
        self._life_span = life_span
        self._timer = None
        self._stopped = False
        self._sweep_time = sweep_time

    @utils.class_method_sync
    def start(self):
        if self._stopped:
            return
        self._timer = dcm_events.register_callback(
            self.clean_sweep, delay=self._sweep_time)

    @utils.class_method_sync
    def stop(self):
        self._stopped = True
        if self._timer is not None:
            dcm_events.cancel_callback(self._timer)
            self._timer = None

    @utils.class_method_sync
    def get_next_page(self, token):
        if token not in self._pages:
            raise exceptions.AgentPageNotFoundException(token)
        pager = self._pages[token]
        (page, remaining) = pager.get_next_page()
        if remaining < 1:
            del self._pages[token]
            token = None
        return page, token

    @utils.class_method_sync
    def new_pager(self, pager, token):
        self._pages[token] = pager

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    @utils.class_method_sync
    def clean_sweep(self):
        too_old = datetime.datetime.now() - \
            datetime.timedelta(seconds=self._life_span)
        kill_keys = []
        for k in self._pages:
            pager = self._pages[k]
            if pager.creation_time < too_old:
                kill_keys.append(k)
        for k in kill_keys:
            del self._pages[k]
        self.start()
