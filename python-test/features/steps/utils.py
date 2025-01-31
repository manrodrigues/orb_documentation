import random
import string
from json import loads, JSONDecodeError
from hamcrest import *
import threading
from datetime import datetime
import socket
import os
import re
import multiprocessing
import json
import jsonschema
from jsonschema import validate

tag_prefix = "test_tag_"


def random_string(k=10):
    """
    Generates a string composed of of k (int) random letters lowercase and uppercase mixed

    :param (int) k: sets the length of the randomly generated string
    :return: (str) string consisting of k random letters lowercase and uppercase mixed. Default:10
    """
    return ''.join(random.choices(string.ascii_letters, k=k))


def safe_load_json(json_str):
    """
    Safely parses a string into a JSON object, without ever raising an error.
    :param (str) json_str: to be loaded
    :return: the JSON object, or None if string is not a valid JSON.
    """

    try:
        return loads(json_str)
    except JSONDecodeError:
        return None


def filter_list_by_parameter_start_with(list_of_elements, parameter, start_with):
    """
    :param (list) list_of_elements: a list of elements
    :param (str) parameter: key of dict whose values will be used to filter the elements
    :param (str) start_with: prefix that will be used to filter the elements that start with it
    :return: (list) a list of filtered elements
    """
    list_of_filtered_elements = list()
    for element in list_of_elements:
        if element[parameter].startswith(start_with):
            list_of_filtered_elements.append(element)
    return list_of_filtered_elements


def insert_str(str_base, str_to_insert, index):
    """

    :param (str) str_base: string in which some letter will be inserted
    :param (str) str_to_insert: letter to be inserted
    :param (int) index: position that letter should be inserted
    :return: (str) string with letter inserted on determined index
    """
    return str_base[:index] + str_to_insert + str_base[index:]


def generate_random_string_with_predefined_prefix(string_prefix, n_random=10):
    """
    :param (str) string_prefix: prefix to identify object created by tests
    :param (int) n_random: amount of random characters
    :return: random_string_with_predefined_prefix
    """
    random_string_with_predefined_prefix = string_prefix + random_string(n_random)
    return random_string_with_predefined_prefix


def create_tags_set(orb_tags):
    """
    Create a set of orb-tags
    :param orb_tags: If defined: the defined tags that should compose the set.
                     If random: the number of tags that the set must contain.
    :return: (dict) tag_set
    """
    tag_set = dict()
    if orb_tags.isdigit() is False:
        assert_that(orb_tags, any_of(matches_regexp("^.+\:.+"), matches_regexp("\d+ orb tag\(s\)"),
                                     matches_regexp("\d+ orb tag")), f"Unexpected regex for tags. Passed: {orb_tags}."
                                                                     f"Expected (examples):"
                                                                     f"If you want 1 randomized tag: 1 orb tag."
                                                                     f"If you want more than 1 randomized tags: 2 orb tags. Note that you can use any int. 2 its only an example."
                                                                     f"If you want specified tags: test_key:test_value, second_key:second_value.")
        if re.match(r"^.+\:.+",
                    orb_tags):  # We expected key values separated by a colon ":" and multiple tags separated
            # by a comma ",". Example: test_key:test_value, my_orb_key:my_orb_value
            for tag in orb_tags.split(", "):
                key, value = tag.split(":")
                tag_set[key] = value
                return tag_set
    amount_of_tags = int(orb_tags.split()[0])
    for tag in range(amount_of_tags):
        tag_set[tag_prefix + random_string(6)] = tag_prefix + random_string(4)
    return tag_set


def check_logs_contain_message_and_name(logs, expected_message, name, name_key):
    """
    Gets the logs from Orb agent container

    :param (list) logs: list of log lines
    :param (str) expected_message: message that we expect to find in the logs
    :param (str) name: element name that we expect to find in the logs
    :param (str) name_key: key to get element name on log line
    :returns: (bool) whether expected message was found in the logs
    """

    for log_line in logs:
        log_line = safe_load_json(log_line)

        if log_line is not None and log_line['msg'] == expected_message:
            if log_line is not None and log_line[name_key] == name:
                return True, log_line

    return False, "Logs doesn't contain the message and name expected"


def remove_empty_from_json(json_file):
    """
    Delete keys with the value "None" in a dictionary, recursively.

    """
    for key, value in list(json_file.items()):
        if value is None:
            del json_file[key]
        elif isinstance(value, dict):
            remove_empty_from_json(value)
    return json_file


def remove_key_from_json(json_file, key_to_be_removed):
    """

    :param json_file: json object
    :param key_to_be_removed: key that need to be removed
    :return: json object without keys removed
    """
    for key, value in list(json_file.items()):
        if key == key_to_be_removed:
            del json_file[key]
        elif isinstance(value, dict):
            remove_key_from_json(value, key_to_be_removed)
    return json_file


def threading_wait_until(func):
    def wait_event(*args, wait_time=0.5, timeout=10, start_func_value=False, **kwargs):
        event = threading.Event()
        func_value = start_func_value
        start = datetime.now().timestamp()
        time_running = 0
        while not event.is_set() and time_running < int(timeout):
            func_value = func(*args, event=event, **kwargs)
            event.wait(wait_time)
            time_running = datetime.now().timestamp() - start
        return func_value

    return wait_event


def return_port_to_run_docker_container(context, available=True, time_to_wait=5):
    """

    :param (bool) available: Status of the port on which agent must try to run. Default: available.
    :param (int) time_to_wait: seconds that threading must wait after run the agent
    :return: (int) port number
    """

    assert_that(available, any_of(equal_to(True), equal_to(False)), "Unexpected value for 'available' parameter")
    if not available:
        unavailable_port = list(context.containers_id.values())[-1]
        return unavailable_port
    else:
        available_port = None
        process_number = multiprocessing.current_process().name.split('-')[-1]
        if process_number.isnumeric():  # if parallel process
            lower_lim_port = 10800 + int(process_number) * 10
            upper_lim_port = lower_lim_port + 10
            port_options_for_process = range(lower_lim_port, upper_lim_port)
        else:  # if sequential process
            port_options_for_process = range(10800, 11000)

        for port in port_options_for_process:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            res = sock.connect_ex(('localhost', port))
            sock.close()
            if res != 0:
                available_port = port
                return available_port
            else:
                # port not available
                continue
    assert_that(available_port, is_not(None), "Unable to find an available port to run orb agent")
    threading.Event().wait(time_to_wait)
    return available_port


def find_files(prefix, suffix, path):
    """
    Find files that match with prefix and suffix condition

    :param prefix: string with which the file should start with
    :param suffix: string with which the file should end with
    :param path: directory where the files will be searched
    :return: (list) path to all files that matches
    """
    result = list()
    for root, dirs, files in os.walk(path):
        for name in files:
            if name.startswith(prefix) and name.endswith(suffix):
                result.append(os.path.join(root, name))
    return result


def get_schema(path_to_file):
    """
    Loads the given schema available

    :param path_to_file: path to schema json file
    :return: schema json
    """
    with open(path_to_file, 'r') as file:
        schema = json.load(file)
    return schema


def validate_json(json_data, path_to_file):

    """
    Compare a file with the schema and validate if the structure is correct
    :param json_data: json to be validated
    :param path_to_file: path to schema json file
    :return: bool. False if the json is not valid according to the schema and True if it is
    """

    execute_api_schema = get_schema(path_to_file)

    try:
        validate(instance=json_data, schema=execute_api_schema)
    except jsonschema.exceptions.ValidationError as err:
        print(err)
        return False, err

    return True
