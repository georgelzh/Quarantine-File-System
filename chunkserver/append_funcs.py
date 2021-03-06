#append_funcs.py - implementation of commands for appending
#Quang Tran - 05 20 20 mm dd yy

import os, datetime, random, math, json, logging, fcntl, base64, requests, traceback
import dateutil.parser

with open("config.json") as config_json:
    config = json.load(config_json)

#Julian Lambert - 05 20 20 mm dd yy
def append(chunk_handle: str, client_ip: str, data_index: str, data: str) -> int:
    """
    The Append function which takes data from the Client

    It expects JSON input from an HTTP POST request in the form: {
        'chunk_handle': <hex>,
		'data_index': <int>,
        'data': <binary_data>
    }

    It implements a gesture toward an LRU (Least Recently Used) Cache by overwriting buffer data when client sends more at the same index. Data is stored in a <chunk_handle>.<client_ip>.<data_index>.buffer file.

    It returns:
        - 0: Success: It worked
        - 1: Failure: Too many Bytes
        - 2: Failure: Yo idk
    """
    #Q: experimental conversaion of bytes encoded as a string using base64
    data = base64.decodebytes(data.encode())
    if len(data) > config["MAX_APPEND_LIMIT"]:
        print(1)
    else:
        # use the chunk_handle, client_ip, and data_index to create the cache file
        #Q: changed some code to write data as bytes
        # using w 'open for writing, truncating the file first' mode so writing at the same index will overwrite old buffer data
        with open("{0}{1}.{2}.{3}.buffer".format(config["WRITE_BUFFER_PATH"], chunk_handle, client_ip, data_index), 'wb+') as buf:
            # dump the recieved data into the buffer file
            buf.write(data)
            return 0
    return 2 # ya--- idk

def append_request(chunk_handle: str, client_ip: str, data_index: str) -> int:
    """
    Request to append the sent data. Note that the client shold only call
    this on the primary chunk.
        chunk_handle: str. The chunk handle of the chunk
        data_index int. The index of the client's append() call
    Return:
        int: An int denoting the status of the request.
            0: The operation succeeded.
            1: The operation failed because the requested chunk has no data in cache to append.
            2: The operation failed because the chunk is too full.
            3: The operation failed for other reasons.
    """
    #Format of filename for write buffer: <chunk_handle>.<client_ip>.chunktemp
    buffer_filename = config["WRITE_BUFFER_PATH"] + "{0}.{1}.{2}.buffer".format(chunk_handle, client_ip, data_index)
    chunk_filename = config["CHUNK_PATH"] + chunk_handle + ".chunk"

    #check if file exists
    try:
        append_file = open(buffer_filename, 'rb')
    except:
        print("buffer not found")
        print(buffer_filename)
        return 1

    #check if write could be performed
    remaining_size = config["CHUNK_SIZE"] - os.path.getsize(chunk_filename) + 9
    if os.path.getsize(buffer_filename) > remaining_size:
        os.remove(buffer_filename)
        return 2

    #time to logic
    #if primary: send request to replicas
    return_code = 0
    chunk_file = open(chunk_filename, 'ab+')

    #file locking: lock the chunk being appended to to not cause corruption
    #https://stackoverflow.com/questions/11853551/python-multiple-users-append-to-the-same-file-at-the-same-time
    #https://docs.python.org/3/library/fcntl.html#fcntl.flock
    fcntl.flock(chunk_file, fcntl.LOCK_EX)

    buffer_size = 1024
    chunk_file.seek(1)
    if chunk_file.read(1) == b'\x01':
        #is primary
        print("am primary")
        try:
            #getting replicas
            with open('./replica.json', 'r+') as f:
                replica_json = json.load(f)
                replicas = replica_json[chunk_handle]

            print(replicas)

            #sending requests to replicas
            #possible improvement: multithread this
            for i in replicas:
                append_request = requests.post("http://{0}/append-request".format(i), json={'chunk_handle': chunk_handle, 'ip_addr': client_ip, 'data_index': data_index})
                print(append_request.status_code)
                if append_request.status_code != 200:
                    return_code = 3
                    raise
                elif append_request.json() != 0:
                    return_code = append_request.json()
                    raise
                else:
                    continue

            #all replicas succeeded peacefully
            #time to append
            while True:
                buf = append_file.read(buffer_size)
                if buf:
                    chunk_file.write(buf)
                else:
                    break

        except Exception as e:
            traceback.print_exc()
            if return_code == 0:
                return_code = 3
            print(return_code)
    else:
        print("am replica")
        while True:
            buf = append_file.read(buffer_size)
            if buf:
                chunk_file.write(buf)
            else:
                break

    fcntl.flock(chunk_file, fcntl.LOCK_UN)
    append_file.close()
    chunk_file.close()

    return return_code
