# Copyright (C) 2013-2019 DNAnexus, Inc.
#
# This file is part of dx-toolkit (DNAnexus platform client libraries).
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may not
#   use this file except in compliance with the License. You may obtain a copy
#   of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

from __future__ import print_function
import os
import sys
import tempfile
import subprocess
import contextlib
import dxpy
import json

class UserContext(object):
    @dxpy.sugar.requires_worker_context
    def __init__(self, api_token):
        api_token = api_token.strip("\n")  # Python adds \n when reading from a file
        self.user_secure_token = {"auth_token": api_token,
                                 "auth_token_type": "Bearer"}
        self.job_id = os.environ["DX_JOB_ID"]
        self.job_security_context = json.loads(os.environ["DX_SECURITY_CONTEXT"])
        self.job_workspace_id = os.environ["DX_WORKSPACE_ID"]

    @dxpy.sugar.requires_worker_context
    def __enter__(self):
        proj = os.environ["DX_PROJECT_CONTEXT_ID"]
        dxpy.set_job_id(None)
        dxpy.set_security_context(self.user_secure_token)
        dxpy.set_workspace_id(proj)
        try:
            dna_config_file = os.path.join(
                os.environ["HOME"], ".dnanexus_config")
            os.remove(dna_config_file)
        except OSError:
            print "As expected, .dnanexus_config not present."
        else:
            print "Could not remove .dnanexus_config file."
        return self

    @dxpy.sugar.requires_worker_context
    def __exit__(self, type, value, traceback):
        print "\nRestoring original Job context"
        dxpy.set_job_id(self.job_id)
        dxpy.set_security_context(self.job_security_context)
        dxpy.set_workspace_id(self.job_workspace_id)

@contextlib.contextmanager
def user_context(api_token):
    """
    Context manager to temporarily set a user DNAnexus context instead of a job context.
    WARNING: This function should only be run on a DNAnexus worker.

    Args:
        api_token: User's API token, recommended to be limited in scope

    Yields:
        An environment that temporarily mimicks a user security context instead of a job security context

    """

@contextlib.contextmanager
def set_env(**environ):
    """
    Context manager generator to temporarily set the subprocess environment variables.

    Args:
        environ (dict): Environment variable to set

    Yields:
        An environment with environment variables set as specified.
        On exit, the environment will return to previous configuration.

    Examples:
        Usage 1: Set environment variable
        # inside environment
        >>> with set_env(PLUGINS_DIR=u'test/plugins'):
        ...    "PLUGINS_DIR" in os.environ
        True

        # outside environment
        >>> "PLUGINS_DIR" in os.environ
        False

        Usage 2: Unset environment variable
        >>> with set_env(PYTHONPATH=''):
        ...    print(os.environ["PYTHONPATH"])
        <BLANKLINE>

        Usage 3: Manipulate multiple variables
        >>> myenv = {"PLUGINS_DIR": u'test/plugins', "PYTHONPATH": u'some/python/path'}
        >>> with set_env(**myenv):
        ...   print(os.environ["PLUGINS_DIR"])
        ...   print(os.environ["PYTHONPATH"])
        test/plugins
        some/python/path
    """
    old_environ = dict(os.environ)
    os.environ.update(environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


class cd:
    """
    Context manager for changing the current working directory

    Args:
        target_path (string): Optional, specify path to cd to
        delete_on_exit (boolean): Optional, specify if directory should be deleted after exiting context. If target_path
        is None, directory is always deleted.

    Note:
        If no args specified, cd() will create an arbitary temp dir and cd to it

    Yields:
        Upon entry, context will be set to the specified directory.
        Upon exit, directory specified with delete_on_exit=True or directory created when no
        args are specified is deleted. If delete_on_exit=False and directory is specified, it is not deleted.

    Source: http://stackoverflow.com/questions/431684/how-do-i-cd-in-python

    Examples:
       with cd():
           do_the_thing
           # this will create a temp directory with a randomly
           # generated name, doe the thing, then delete the temp dir

       with cd(my_file_dir):
           do_the_thing
           # this will do the thing in my_file_dir and not delete the directory

       with cd(target_path=my_temp_dir, delete_on_exit=True):
           do_the_thing
           # this will create a temp dir with path my_temp_dir, do the thing,
           # then delete the temp dir
    """

    def __init__(self, target_path=None, delete_on_exit=False):
        if target_path is not None:
            if os.path.exists(target_path):
                self.newPath = target_path
            else:
                self.newPath = tempfile.mkdtemp(dir=target_path)
            self.removeFolder = delete_on_exit
        else:
            self.newPath = tempfile.mkdtemp()
            self.removeFolder = True

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)
        if self.removeFolder:
            subprocess.check_call(['rm', '-rf', self.newPath], shell=False)

@contextlib.contextmanager
def temp(*args, **kwargs):
    """Context manager that yields a temp file name and deletes the file
    before exiting.
    Args:
        *args: positional arguments passed to mkstemp
        **kwargs: keyword arguments passed to mkstemp
    Examples:
        >>> with temp() as fn:
        >>>     with open(fn, "wt") as out:
        >>>         out.write("foo")
    """
    _, fname = tempfile.mkstemp(*args, **kwargs)
    try:
        yield fname
    finally:
        if os.path.exists(fname):
            os.remove(fname)


@contextlib.contextmanager
def fifo(name=None):
    """
    Create a FIFO, yield it, and delete it before exiting.
    Args:
        name: The name of the FIFO, or None to use a temp name.
    Yields:
        The name of the FIFO
    """
    if name:
        os.mkfifo(name)
        yield name
    else:
        with temp() as name:
            os.mkfifo(name)
            yield name

    if os.path.exists(name):
        os.remove(name)


if __name__ == "__main__":
    import doctest

    test_failures = doctest.testmod()[0]
    if test_failures > 0:
        print("Encountered {0} failures".format(test_failures))
        sys.exit(1)
    else:
        print("All tests passed.")
