# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Fraunhofer FKIE/US, Alexander Tiderko
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Fraunhofer nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import unittest
import time

from node_manager_daemon_fkie.common import interpret_path
from node_manager_daemon_fkie.file_item import FileItem
from node_manager_daemon_fkie.server import GrpcServer
import node_manager_daemon_fkie.remote as remote
import node_manager_daemon_fkie.file_stub as fstub
import node_manager_daemon_fkie.launch_stub as lstub
import node_manager_daemon_fkie.exceptions as exceptions

PKG = 'node_manager_daemon_fkie'


class TestGrpcServer(unittest.TestCase):
    '''
    '''

    def setUp(self):
        self.server = GrpcServer()
        self.server.start('[::]:12311')
        url = 'localhost:12311'
        channel = remote.get_insecure_channel(url)
        self.fs = fstub.FileStub(channel)
        self.ls = lstub.LaunchStub(channel)
        self.test_include_file = "%s/resources/include_dummy.launch" % os.getcwd()

    def tearDown(self):
        #self.server.shutdown()
        pass

    def test_list_path(self):
        rpp = os.environ['ROS_PACKAGE_PATH'].split(':')
        result = self.fs.list_path('')
        self.assertEqual(len(result), len(rpp), "wrong count of items in the root path, got: %s, expected: %s" % (len(result), len(rpp)))
        count_dirs = [p.path for p in result if p.type in [FileItem.DIR, FileItem.PACKAGE]]
        self.assertEqual(len(count_dirs), len(rpp), "wrong count of directories in the root path, got: %s, expected: %s" % (len(count_dirs), len(rpp)))
        try:
            result = self.fs.list_path('/xyz')
            self.fail("`list_path` did not raises `OSError` on not existing path `/xyz`")
        except OSError:
            pass
        except Exception as err:
            self.fail("`list_path` raises wrong Exception on not existing path `/xyz`, got: %s, expected: `OSError`" % type(err))

    def test_get_file_content(self):
        file_size, file_mtime, file_content = self.fs.get_file_content(self.test_include_file)
        self.assertEqual(file_size, 842, "wrong returned file size, got: %s, expected: %s" % (file_size, 842))
        self.assertEqual(len(file_content), 842, "wrong size of the content, got: %s, expected: %s" % (len(file_content), 842))
        try:
            result = self.fs.get_file_content('xyz')
            self.fail("`get_file_content` did not raises `IOError` on not existing path `/xyz`")
        except IOError:
            pass
        except Exception as err:
            self.fail("`get_file_content` raises wrong Exception on not existing path `/xyz`, got: %s, expected: `IOError`" % type(err))

    def _count_all_includes(self, file_list):
        result = len(file_list)
        for linenr, path, exists, inc_files in file_list:
            result += self._count_all_includes(inc_files)
        return result

    def test_get_included_files(self):
        path = interpret_path("$(find node_manager_daemon_fkie)/tests/resources/include_dummy.launch")
        file_list = self.ls.get_included_path(path, recursive=True, unique=True, include_pattern=[])
#        for linenr, path, exists, file_list in inc_files:
        self.assertEqual(len(file_list), 4, "Count of unique included, recursive files is wrong, got: %d, expected: %d" % (len(file_list), 4))
        file_list = self.ls.get_included_path(path, recursive=False, unique=True, include_pattern=[])
        self.assertEqual(len(file_list), 3, "Count of unique included files while not recursive search is wrong, got: %d, expected: %d" % (len(file_list), 3))
        file_list = self.ls.get_included_path(path, recursive=False, unique=False, include_pattern=[])
        self.assertEqual(len(file_list), 6, "Count of recursive, not unique included files is wrong, expected: %d, got: %d" % (len(file_list), 6))
        file_list = self.ls.get_included_path(path, recursive=True, unique=False, include_pattern=[])
        self.assertEqual(len(file_list), 6, "Count of included files in root file is wrong, expected: %d, got: %d" % (len(file_list), 6))
        self.assertEqual(self._count_all_includes(file_list), 10, "Count of recursive included files is wrong, expected: %d, got: %d" % (self._count_all_includes(file_list), 10))
        self.assertEqual(file_list[0][0], 6, "Wrong line number of first included file, expected: %d, got: %d" % (file_list[0][0], 6))
        #self.assertEqual(file_list[0][1], file_list[0][3][0][1], "Wrong root path of second included file, expected: %s, got: %s" % (file_list[0][1], file_list[0][3][0][1]))
        self.assertEqual(file_list[1][0], 9, "Wrong line number of second included file, expected: %d, got: %d" % (file_list[1][0], 9))
        self.assertEqual(file_list[2][0], 10, "Wrong line number of third included file, expected: %d, got: %d" % (file_list[2][0], 10))


    def test_load_launch(self):
        args = {}
        path = ''
        request_args = True
        nexttry = True
        ok = False
        launch_file = ''
        package = 'node_manager_daemon_fkie'
        launch = 'description_example.launch'
        try:
            launch_file, _argv = self.ls.load_launch(package, launch, path=path, args=args, request_args=request_args)
            self.fail("`load_launch` did not raises `exceptions.LaunchSelectionRequest` on multiple launch files")
        except exceptions.LaunchSelectionRequest as lsr:
            path = lsr.choices[-1]
        except Exception as err:
            self.fail("`load_launch` raises wrong Exception on multiple launch files, got: %s, expected: `exceptions.LaunchSelectionRequest`: %s" % (type(err), err))
        try:
            launch_file, _argv = self.ls.load_launch(package, launch, path=path, args=args, request_args=request_args)
            self.fail("`load_launch` did not raises `exceptions.ParamSelectionRequest` on args requests")
        except exceptions.ParamSelectionRequest as psr:
            request_args = False
            args = psr.choices
        except Exception as err:
            self.fail("`load_launch` raises wrong Exception on args requests, got: %s, expected: `exceptions.ParamSelectionReques`: %s" % (type(err), err))
        request_args = False
        try:
            launch_file, _argv = self.ls.load_launch(package, launch, path=path, args=args, request_args=request_args)
        except Exception as err:
            self.fail("`load_launch` raises unexpected exception, got: %s, expected: no error" % type(err))
        try:
            launch_file, _argv = self.ls.load_launch(package, launch, path=path, args=args, request_args=request_args)
            self.fail("`load_launch` did not raises `exceptions.AlreadyOpenException` on load an already loaded file")
        except exceptions.AlreadyOpenException as aoe:
            request_args = False
            args = psr.choices
        except Exception as err:
            self.fail("`load_launch` raises wrong Exception on second reload, got: %s, expected: `exceptions.AlreadyOpenException`: %s" % (type(err), err))

    def test_reload_launch(self):
        path = interpret_path("$(find node_manager_daemon_fkie)/tests/resources/include_dummy.launch")
        try:
            launch_file, _argv = self.ls.reload_launch(path)
            self.fail("`load_launch` did not raises `exceptions.ResourceNotFoundt` on reload launch file")
        except exceptions.ResourceNotFound as rnf:
            pass
        except Exception as err:
            self.fail("`load_launch` raises wrong Exception on reload launch file, got: %s, expected: `exceptions.ResourceNotFoundt`: %s" % (type(err), err))

if __name__ == '__main__':
    import rosunit
    rosunit.unitrun(PKG, os.path.basename(__file__), TestGrpcServer)

