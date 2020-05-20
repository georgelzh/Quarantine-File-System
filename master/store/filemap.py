#!/usr/bin/env python3
"""
 filemap.py - Structure that quickly returns chunkhandles and
              chunkservers from a filename.
 Date: 5/17/2020
"""

"""
The reason the FileMap and MetadataStore classes are broken up is because 
the FileMap class can be refactored to make things much faster later on
without complicating or breaking the interface with other components
"""


class FileMap:
    def __init__(self, state = {}):
        self.files = {"":{}} if not state else state["files"]
        #each filename-> [[chunkhandle, size], [chunkhandle2, size], ...]
        self.chunkhandle_map = {} if not state else ["chunkhandles"]

    # Break string up into a format that can be used to search the filemap
    def process_path(path):
        return path.split("/")

    # Return dictionary that contains the state of the FileMap
    def checkpoint(self):
        return {
                "files":self.files, 
                "chunkhandles":self.chunkhandle_map
               }

    # Retrieve chunk
    def retrieve(self, path, index, container = False):
        if not container: container = self.files
        path = path if not type(path) == type('string') else process_path(path)
        content = container[path[0]]
        if path.length() == 1:
            return content[index] + [self.get_chunkhandles(content[index][0])]
        else:
            return self.retrieve(path[1:], index, content)

    # Add or mutate a chunk
    def update(self, path, index, value, replicas = False, container = False)
        if not container: container = self.files
        path = path if not type(path) == type('string') else process_path(path)
        elif path.length() == 1:
            # Update if the chunk exists
            if replicas: self.chunkhandle_map[value[0]] = replicas
            if content.length() - 1 <= index:
                if value.length() == 1:
                    content[index][1] = value
                else:
                    content[index] = value
                return content
            else:
                # Append to chunk list if it doesn't exist
                content[index] += [value]
                if replicas: self.chunkhandle_map[value[0]] = replicas
                return content
        else:
            content[path[0]] = self.update(path[1:], index, value, replicas, content[path[0]])
            return content

    def make_path(self, path, top = True, directory = False, container = False):
        path = path if not type(path) == type('string') else process_path(path)
        if not container: container = self.files
        if top and path.length() == 1:
            return False
        elif top:
            return self.make_path(path[1:], False, path[-1]=="", container[path[0]])
        elif path.length() == 1:
            if path[0] in container:
                return False
            else:
                container[path] = {} if directory else []
                return container
        else:
            content =  self.make_path(path[1:], False, path[-1]=="", container[path[0]])
            return content
            
            
    def verify_path(self, path, container = False):
        path = path if not type(path) == type('string') else process_path(path)
        if not container: container = self.files
        if path.length() == 1:
            return path[0] in container
        else:
            return verify_path(path[1:], content[path[0]])
        


    #Add an active server or remove an inactive one
    def toggle(self, chunkserver, on):
        # This is slow right now, but I don't have an intelligent way
        # of mapping *cries*
        for chunkhandle in self.chunkhandle_map:
            if not on:
                if chunkserver in self.chunkhandle_map[chunkhandle]:
                    del self.chunkhandle_map[chunkhandle][chunkserver]
            else:
                if chunkserver not in self.chunkhandle_map[chunkhandle]:
                    self.chunkhandle_map[chunkhandle] += [chunkserver] 
                    

    def get_chunkservers(self, chunkhandle):
        return self.chunkhandle_map[chunkhandle]

    def list_chunkservers(self):
        # o(mn) where m is chunkservers and n is chunkhandles 
        #*cries again*
        chunkservers=[]
        for chunkhandle in self.chunkhandle_map:
            for chunkserver in self.chunkhandle_map[chunkhandle]:
                if chunkserver not in chunkservers:
                    chunkservers += [chunkserver]
        return chunkservers


