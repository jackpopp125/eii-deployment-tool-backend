# Copyright (c) 2021 Intel Corporation.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import os
import json
import logging
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

DESCRIPTION = """
EII Deployment Tool Backend provides REST APIs to Configure, build and deploy your
usecases

## Project

* **Project Load**
* **Project Store**


"""
app = FastAPI(
    title = "Intel© Edge Insights for Industrial (EII) REST APIs",
    description = DESCRIPTION,
    version = "0.0.1"
)


class Util:
    """
    Class for various generic utility functions

    """

    IE_DIR = "/app/IEdgeInsights/"
    EII_CONFIG_PATH = IE_DIR + "build/provision/config/eii_config.json"
    EII_PROJECTS_PATH = IE_DIR + "build/projects/"
    JSON_EXT = ".json"

    def __init__(self):
        error = None
        # Initilize logging
        env_log_level=os.environ.get("LOG_LEVEL", "INFO")

        if env_log_level == "DEBUG":
            logging_format = "[%(funcName)(): %(lineno)s  ] %(message)s"
            logging_level = logging.DEBUG
        elif env_log_level == "INFO":
            logging_format = "%(message)s"
            logging_level = logging.INFO
        elif env_log_level == "ERROR":
            logging_format = "%(message)s"
            logging_level = logging.ERROR
        else:
            logging_format = "%(message)s"
            logging_level = logging.INFO
            error = "Invalid log level {}. Resetting log level to INFO" \
                    .format(env_log_level)

        logging.basicConfig(level=logging_level, format=logging_format)
        self.logger = logging.getLogger(__name__)
        if error:
            self.logger.ERROR(error)


    def load_file(self, path):
        """Reads a file and return its contents as utf-8 string

        :param path: file path
        :type path: str
        :return: status of operation
        :rtype: bool
        :return: error description
        :rtype: str
        :return: file contents
        :rtype: str
        """
        try:
            data = None
            status = True
            error_detail = ""
            with open(path, "r", encoding='utf8') as filehandle:
                data = filehandle.read()
            if isinstance(data, bytearray) or isinstance(data, bytes):
                data = data.decode('utf-8')
        except Exception as e:
            status = False
            error_detail = "failed to read file: [{}]: {}".format(path, e)
        return status, error_detail, data


    def store_file(self, path, data, overwrite=False):
        """Writes the specified data to file

        :param path: file name
        :type path: str
        :param data: data to write
        :type data: str/bytearray
        :param overwrite: Whether to replace existing file
        :type overwrite: bool
        :return: status of operation
        :rtype: bool
        :return: error description
        :rtype: str
        """
        try:
            error_detail = ""
            mode = None
            status = True
            if overwrite:
                mode = "w"
            else:
                mode = "a"

            with open(path, mode) as filehandle:
                if isinstance(data, str):
                    filehandle.write(data)
                elif isinstance(data, bytearray) or isinstance(data, bytes):
                    filehandle.write(data.decode('utf-8'))
                else:
                    status = False
                    error_detail = "Internal error: Unhandled type: {}".format(type(data))
                    self.logger.error(error_detail)
        except Exception as e:
            status = False
            error_detail = "Failed to write file: [{}]: {}".format(path, e)
            self.logger.error(error_detail)

        return status, error_detail


    def get_consolidated_config(self, path = None):
        """Get specified/current config data

        :param path: path for the config file
        :type path: str
        :return: status
        :rtype: bool
        :return: error description
        :rtype: str
        :return: config data
        :rtype: dict
        """
        status = False
        eii_config = None

        if path is None:
            path = util.EII_CONFIG_PATH
        try:
            status, error_detail, eii_config_str = self.load_file(path)
            if status:
                eii_config = json.loads(eii_config_str)

        except Exception as e:
            status = False
            error_detail = "exception while reading eii_config.json: {}".format(e)
            self.logger.error(error_detail)

        return status, error_detail, eii_config


    def store_consolidated_config(self, config, path = None):
        """Write config data to the specified/current config file

        :param config: config data
        :type config: dict
        :param path: path to store the config file
        :type path: str
        :return: status of operation
        :rtype: bool
        :return: error description
        :rtype: str
        """
        status = False
        if path is None:
            path = util.EII_CONFIG_PATH
        try:
            status, error_detail = self.store_file(path, json.dumps(config, indent=4), True)
        except Exception as e:
            error_detail = "exception while writing {}: {}".format(path, e)
            self.logger.error(error_detail)

        return status, error_detail


def do_load_project(name):
    """Returns the config data for an existing project

    :param name: name for the project
    :type name: str
    :return: status of operation
    :rtype: bool
    :return: error description
    :rtype: str
    :return: config data
    :rtype: dict
    """
    path = util.EII_PROJECTS_PATH + name + util.JSON_EXT
    return util.get_consolidated_config(path)


def do_store_project(name, replace = True):
    """Create config file for the current unsaved project

    :param name: name for the project
    :type name: str
    :param replace: Whether replace existing file
    :type replace: bool
    :return: status of operation
    :rtype: bool
    :return: error description
    :rtype: str
    """
    status, error_detail, config = util.get_consolidated_config()
    if status:
        path = util.EII_PROJECTS_PATH + name + util.JSON_EXT
        if replace is False and os.path.isfile(path):
            util.logger.error("Error: destination file {} already exists!".format(path))
            status = False
        else:
            status, error_detail = util.store_consolidated_config(config, path)
    return status, error_detail


def make_response_json(status, data, error_detail):
    """Common function for creating the response object for all the APIs

    :param status: status of repsonse
    :type status: bool
    :param data: response data
    :type data: stringified json
    :param errdesc: Description of error, if any
    :type error_detail: str
    :return: response data
    :rtype: json
    """

    if status is False or data in (None, ""):
        data = {}
    if status:
        error_detail = ""

    #TBD
    console_log = ""
    response_json = {
                        "data": data,
                        "status_info": {
                            "status": status,
                            "error_detail": error_detail,
                            "console": console_log
                        }
                    }

    return response_json


##############################################################################
# Parmeter class definitions

class ProjectInfo(BaseModel):
    name: str = Field(..., title="Project name", max_length=128)

class ResponseStatus(BaseModel):
    status: bool = Field(..., title="Error status")
    error_detail: str = Field(..., title="Error detail")
    console: str = Field(..., title="Console log")

class Response(BaseModel):
    data: str = Field(..., title="Response Data")
    status_info: ResponseStatus = Field(..., title="Response Status")

#
# API defnitions
#

@app.post('/eii/ui/project/load',
    response_model=Response,
    responses={200: {"model": Response}}
)
def project_load(param: ProjectInfo):
    status, error_detail, info = do_load_project(param.name)
    return make_response_json(status, json.dumps(info), error_detail)


@app.post('/eii/ui/project/store',
    response_model=Response,
    responses={200: {"model": Response}}
)
def project_store(param: ProjectInfo):
    status, error_detail = do_store_project(param.name)
    return make_response_json(status, " ", error_detail)


util = Util()

if __name__ == '__main__':
    if len(sys.argv) != 2 or int(sys.argv[1]) <= 0:
        util.logger.error("Error: Invalid/missing arguments!")
        sys.exit(0)

    server_port = int(sys.argv[1])
    uvicorn.run(app, host="0.0.0.0", port=server_port)