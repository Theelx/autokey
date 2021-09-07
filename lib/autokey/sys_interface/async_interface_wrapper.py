# Copyright (C) 2021 BlueDrink9
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import threading
import typing
import time
import queue

from autokey import common
from autokey.model.button import Button
from autokey.interface import XRecordInterface
from autokey.scripting import Clipboard as APIClipboard
from autokey.sys_interface.abstract_interface import AbstractSysInterface, AbstractMouseInterface, AbstractWindowInterface

logger = __import__("autokey.logger").logger.get_logger(__name__)

# This tuple is used to return requested window properties.
WindowInfo = typing.NamedTuple("WindowInfo", [("wm_title", str), ("wm_class", str)])

class AsyncInterfaceWrapper(threading.Thread, AbstractMouseInterface, AbstractWindowInterface, AbstractSysInterface):
    """
    This class wraps the methods of an interface to the system (for keyboard,
    window, mouse etc) in a queue processed by threads.
    """

    def __init__(self, toWrap: AbstractSysInterface):
        threading.Thread.__init__(self)
        self.toWrap = toWrap
        toWrap.__enqueue = self.__enqueue
        self.setDaemon(True)
        self.setName("Interface-thread")

        # Event loop
        self.eventThread = threading.Thread(target=self.__eventLoop)
        self.queue = queue.Queue()

        # # Event listener
        # self.listenerThread = threading.Thread(target=self.__flush_events_loop)

        # self.__initMappings()

        self.__ignoreRemap = False

        self.eventThread.start()

    def start(self):
        self.toWrap.start()

    def __enqueue(self, method: typing.Callable, *args):
        self.queue.put_nowait((method, args))

    def __eventLoop(self):
        while True:
            method, args = self.queue.get()

            if method is None and args is None:
                break
            elif method is not None and args is None:
                logger.debug("__eventLoop: Got method {} with None arguments!".format(method))
            try:
                method(*args)
            except Exception as e:
                logger.exception("Error in X event loop thread: {}".format(e))

            self.queue.task_done()

    def cancel(self):
        # if type(self.toWrap) is XRecordInterface:
        #     self.toWrap.localDisplay.record_disable_context(self.toWrap.ctx)
        logger.debug("AsyncInterface: Try to exit event thread.")
        self.queue.put_nowait((None, None))
        logger.debug("AsyncInterface: Event thread exit marker enqueued.")
        self.eventThread.join()
        self.toWrap.cancel()
        self.join()


    def flush(self):
        self.__enqueue(self.toWrap.flush)

    def on_keys_changed(self):
        """
        Update interface when keyboard layout changes.
        """
        # TODO consider moving this logic back to main class later, if timing isn't an issue.
        if not self.__ignoreRemap:
            logger.debug("Recorded keymap change event")
            self.__ignoreRemap = True
            time.sleep(0.2)
            self.__enqueue(self.toWrap.on_keys_changed)
        else:
            logger.debug("Ignored keymap change event")

    def press_key(self, keyName):
        self.__enqueue(self.toWrap.press_key, keyName)
    def release_key(self, keyName):
        self.__enqueue(self.toWrap.release_key, keyName)
    def handle_keypress(self, keyCode):
        self.__enqueue(self.toWrap.handle_keypress, keyCode)
    def handle_keyrelease(self, keyCode):
        self.__enqueue(self.toWrap.handle_keyrelease, keyCode)
    def grab_keyboard(self):
        self.__enqueue(self.toWrap.grab_keyboard)
    def ungrab_keyboard(self):
        self.__enqueue(self.toWrap.ungrab_keyboard)
    def grab_hotkey(self, item):
        self.__enqueue(self.toWrap.grab_hotkey)
    def ungrab_hotkey(self, item):
        self.__enqueue(self.toWrap.ungrab_hotkey)

    def send_string(self, string):
        self.__enqueue(self.toWrap.send_string, string)
    def send_key(self, key_name):
        self.__enqueue(self.toWrap.send_key, key_name)
    def send_modified_key(self, key_name, modifiers):
        self.__enqueue(self.toWrap.send_modified_key, key_name, modifiers)
    def click_midde_mouse_button(self):
        self.__enqueue(self.toWrap.click_middle_mouse_button)

    def fake_keydown(self, key_name):
        self.__enqueue(self.toWrap.fake_keydown, key_name)
    def fake_keyup(self, key_name):
        self.__enqueue(self.toWrap.fake_keyup, key_name)
    def fake_keypress(self, key_name):
        self.__enqueue(self.toWrap.fake_keypress, key_name)

# class AbstractMouseInterface(ABC, metaclass=ABCMeta):
    """
    This class aims to define all the methods needed to interact with the underlying
    mouse system. (eg X11)
    """

    def send_mouse_click(self, xCoord, yCoord, button, relative):
        self.__enqueue(self.toWrap.send_mouse_click, xCoord, yCoord, button, relative)
    def mouse_press(self, xCoord, yCoord, button):
        self.__enqueue(self.toWrap.mouse_press, xCoord, yCoord, button)
    def mouse_release(self, xCoord, yCoord, button):
        self.__enqueue(self.toWrap.mouse_release, xCoord, yCoord, button)
    def mouse_location(self):
        self.toWrap.mouse_location()
    def relative_mouse_location(self, window=None):
        self.toWrap.relative_mouse_location(window)
    def scroll_down(self, number):
        for i in range(0, number):
            self.__enqueue(self.toWrap.scroll_down, Button.SCROLL_DOWN)
    def scroll_up(self, number):
        for i in range(0, number):
            self.__enqueue(self.toWrap.scroll_down, Button.SCROLL_UP)
    def move_cursor(self, xCoord, yCoord, relative=False, relative_self=False):
        self.__enqueue(self.toWrap.move_cursor, xCoord, yCoord, relative, relative_self)
    def send_mouse_click_relative(self, xoff, yoff, button):
        self.__enqueue(self.toWrap.send_mouse_click_relative, xoff, yoff, button)
    def handle_mouseclick(self, button, x, y):
        self.__enqueue(self.toWrap.handle_mouseclick, button, x, y)

    def click_middle_mouse_button(self):
        self.__enqueue(self.click_middle_mouse_button)

    def get_window_class(self, window, traverse) -> str:
        return self.toWrap.get_window_class(window=window, traverse=traverse)
    def get_window_info(self, window, traverse: bool) -> WindowInfo:
        return self.toWrap.get_window_info(window=window, traverse=traverse)
    def get_window_title(self, window, traverse) -> str:
        return self.toWrap.get_window_title(window=window, traverse=traverse)
