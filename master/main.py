#!/usr/bin/env python3
"""
    main.py - Provides a Flask API to receive requests from both the client and chunkservers
    Date: 5/12/2020
"""

import threading
from flask import Flask, jsonify
from file_management import *
from leases import *


app = Flask(__name__)

@app.route("/")
def example():
    return "QFS master!"


# need to do some change---should use metadata_handler.get_chunk(file_path), without index,
# you get all chunk info for the file. slice it up from there. return json

# need to reform this function so that chunkserver can call and create new chunks or files
@app.route('/fetch/<path:file_path>/<string:command>', methods=['GET'])
@app.route('/fetch/<path:file_path>/<string:command>/<int:chunk_index>', methods=['GET'])
def fetch(file_path, command, chunk_index=None):
    """
    Caller: Client
    :param file_path: path of the file. if you have a file under "/school/cs/" called work work.txt
                            then you should have "/school/cs/work/" # you can keep suffix of the file if you'd like
                            it's optional and it does not affect how you use our system.
    :param chunk_index: A specific part of the file being requested. 
                It's not needed when chunkserver is adding a new chunk to an existing file. 
    :return: if succeeds: chunk handle and chunk locations as JSON
                if fails: return error in json format {"error": "error messagesss"}
    """
    global metadata_handler
    file_path = "/" + file_path
    error = {"error": "invalid file path"}
    json_response = {}

    if metadata_handler.verify_path(file_path) == False:
        return jsonify(error)

    # for a read
    if command == "r":
        # since this function takes a list of index, so I used [chunk_index] to make it a list
        chunk_info = metadata_handler.get_chunk(file_path)
        json_response = json_response[file_path] = chunk_info
        return jsonify(json_response)
    
    # for return the last chunk of the file
    elif command == "a":
        chunk_info = metadata_handler.get_chunk(file_path)
        json_response = json_response[file_path] = chunk_info
        return jsonify(json_response) # return json packaged chunk info
    
    elif command == "ac":
        chunk_info = create_new_chunk(file_path)
        json_response = json_response[file_path] = chunk_info
        return jsonify(json_response)

@app.route('/create/file/<path:new_file_path>', methods = ['GET'])
def create_file(new_file_path, file_size):
    """
    Caller: Client
    :param new_file_path: path of the file being created 
    :param file_size: bytes of the file
    :return: all the chunk handles being created in json file under the key called "chunk_handle".  
                    don't know the exact format yet is in the value of the key yet, need to ask
    """
    global metadata_handler
    new_file_path = "/" + new_file_path
    error = {"error": "invalid file path"}
    json_response = {"chunk_info": None}
    try:
        metadata_handler.create_path(new_file_path)
        create_new_chunk(new_file_path)
        chunk_info = metadata_handler.get_chunk(new_file_path)[-1]
        json_response["chunk_info"] = chunk_info
        return jsonify(json_response)
    except:
        return jsonify(error)


@app.route('/create/directory/<path:new_directory_path>', methods = ['GET'])
def create_directory(new_directory_path):
    """
    Caller: Client
    :param new_directory_path: path of the directory will be being created
    :return: json file. if success, return {"success": "directory created"}
                    if failed, return {"error": "parent directory does not exist"}
    """
    new_directory_path = "/" + new_directory_path
    error = {"error": "parent directory does not exist"}
    success = {"success": "directory created"}
    output = create_new_directory(new_directory_path)

    if output == False:
        return jsonify(error)
    else:
        return jsonify(success)


@app.route('/heartbeat/<string:chunk_server>/<string:chunk_server_state>', methods=['GET'])
def heartbeat(chunk_server,chunk_server_state):
    """
    Caller: Chunkserver
    :param chunk_server_ip: chunk_server_ip/dns
    :param chunk_server_state: string, True(chunk server is available), False(unavailable) 
    :return: status code 200 means"OK"; code 500 means "error" ; code 400 means invalid inputs
    """
    if chunk_server == None or chunk_server_state == None:
        return str(400)
    try:
        global live_chunk_server_set
        if chunk_server_state == "False":
            # remove from the set if its been set False
            to_remove = None
            for chunkserver, date_time in live_chunk_server_set:
                if chunkserver == chunk_server:
                    to_remove = (chunkserver, date_time)
                    break
            live_chunk_server_set.remove(to_remove)

        elif chunk_server_state == "True":
            live_chunk_server_set.add((chunk_server, datetime.now()))
    except:
        return str(500)
    return str(200)

@app.route('/lease-request/<string:chunk_handle>/<string:chunk_server_addr>/<int:chunk_size>', methods=['GET'])
def lease_request(chunk_handle, chunk_server_addr, chunk_size):
    """
    Caller: Chunkserver
    :param chunk_handle: Chunk handle in hex for a lease  
    :return: Boolean (True) if the operation succeeded 
    """
    global lease
    global metadata_handler
    metadata_handler.mutate_chunk(chunk_handle, chunk_size)
    if lease.grant_lease(chunk_handle, chunk_server_addr) == True:
        return lease.chunk_lease
    else:
        return False

@app.route('/liveserver', methods = ['GET'])
@app.route('/liveserver/', methods = ['GET'])
def live_server():
    global live_chunk_server_set
    dictionary = {}
    counter = 1
    for live_server in live_chunk_server_set:
        dictionary[counter] = live_server
        counter += 1
    return jsonify(dictionary)

@app.route('/metadata')
@app.route('/metadata/')
def metadata():
    global metadata_handler
    return jsonify(metadata_handler.store.files)

if __name__ == "__main__":
    # # test lease
    # lease.grant_lease("11","127.0.0.1")
    # output = "127.0.0.1"
    # assert lease.chunk_lease["11"]['primary'] == output, "lease grant failed"

    thread_update_live_server = threading.Thread(target=update_live_chunk_server) # update available chunkserver, every 30s, runs forever
    thread_app_run = threading.Thread(target=app.run)
    thread_update_live_server.start()
    thread_app_run.start()

"""
take path as input in flask
https://flask.palletsprojects.com/en/1.1.x/quickstart/
"""