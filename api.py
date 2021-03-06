# -*- coding: utf-8 -*-
# Copyright (c) 2013 Molly White
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__all__ = ['Document']

import codecs, json, logging, os, pickle, re
from sys import exit
from urllib import parse, request
from collections import OrderedDict
from math import ceil
from time import time
from exceptions import APIError, NoPagesReturned, PickleEmpty

class Document(object):
    '''This class reads each page (in the main namespace, not the Index pages) and creates an
    ordered dictionary. The keys in this dictionary are the names of the .djvu files, and the values
    are lists of the page numbers each main page uses.'''
    
    def __init__(self):
        # Bare API call, minus the page title
        self.api_json = "http://en.wikisource.org/w/api.php?format=json&action=query&titles={0}&prop=revisions&rvprop=content"
        self.api_txt = "http://en.wikisource.org/w/api.php?format=txt&action=query&titles={0}&prop=revisions&rvprop=content"
        self.api_attribute = "http://en.wikisource.org/w/api.php?format=json&action=query&prop=revisions&titles={0}&rvprop=user&rvlimit=500"
        self.prefix = parse.quote("United States – Vietnam Relations, 1945–1967: A Study Prepared by the Department of Defense".encode())
        self.pages = OrderedDict()
        self.page_list = []
        self.users = [] # List of any editor who has contributed to any of the Pentagon Papers pages
        self.num_pages = 0
        
        self.recreated = False # Whether the queries were repeated.
        self.directory = os.curdir
        self.logger = logging.getLogger("W2L")
        
    def attribute(self):
        # TODO: This is slow as all hell (it took me 6 minutes) and will only get worse as more
        # pages are added. Try to figure out if there's any way to speed it up.
        
        # If the queries haven't been made again and users.txt exists, just use the old list.
        if not self.recreated and os.path.exists('users.txt'):
            self.logger.debug("Reading saved list of contributors.")
            with codecs.open("users.txt", 'r', 'utf-8') as file:
                users = file.readlines()
                for user in users:
                    user = user.rstrip('\n')
                    self.users.append(user)                    
        # Can't use the old list because it doesn't exist or new queries were made.
        else:
            self.logger.debug("Getting list of contributors.")
            start_time = time()
            if not self.page_list:
                if os.path.exists('eachpage.pkl'):
                    self.logger.debug("Attribution page list found. Unpickling.")
                    with open('eachpage.pkl', 'rb') as file:
                        try:
                            self.page_list = pickle.load(file)
                            if len(self.page_list) == 0:
                                raise PickleEmpty()
                        except PickleEmpty:
                            self.logger.exception("Pickle file is empty. Delete the eachpage.pkl "
                                                  "and pagelist.pkl files and try running the "
                                                  "program again.")
                            exit()
                        except Exception as e:
                            self.logger.exception("Error occurred when trying to unpickle the "
                                                  "list of pages for attribution: {}"
                                                  .format(e.strerror))
                else:
                    raise APIError()
            for page in self.page_list:
                query = self.api_attribute.format(page)
                response = json.loads(request.urlopen(query).read().decode('utf-8'))
                rev_id = list(response["query"]["pages"].keys())[0]
                user_list = response["query"]["pages"][rev_id]["revisions"]
                for entry in user_list:
                    try:
                        user = entry["user"]
                    except KeyError:
                        # This will catch redacted usernames
                        pass
                    if user not in self.users:
                        self.users.append(user)
            with codecs.open("users.txt", 'w', 'utf-8') as file:
                for user in self.users:
                    file.write(user + '\n')
            self.logger.debug("List of users compiled in {} seconds."
                              .format(round(time()-start_time, 2)))
        return self.users
            
    def call(self):
        '''Performs the calls to the API and stores the results as numbered text files. This
        function checks if the /raw directory already exists to avoid querying the API multiple
        times. Files are stored in the following format:
        
        /Wikipedia-to-LaTeX        <-- project folder
        +-- /raw                   <-- folder for all raw text files pulled from the API 
        |   +-- /0                 <-- folder for the first main page (in this case, '/Front matter')
        |   |   +-- 0.txt          <-- text from the first API call (in this case, pages 1-7)
        |   |   +-- 1.txt          <-- text from the second API call (in this case, page 11)
        |   +-- /1                 <-- folder for the second main page ('/')
        |   |   +-- 0.txt          <-- text from the first API call (page 9)
        |   |   +-- 1.txt          <-- text from the second API call (page 10)
        |   +-- /2                 <-- folder for the third main page ('/I. Vietnam and the U.S., 1940–1950')
        |   |   +-- 0.txt          <-- text from the first API call (in this case, pages 1-4)
        |   +-- /3                 <-- folder for the fourth main page ('/I. A. U.S. Policy, 1940–50')
        |   |   +-- 0.txt          <-- text from the first API call (pages 5-9)
        |   |   +-- 1.txt          <-- text from the second API call (pages 10-59)
        |   |   +-- 2.txt          <-- text from the third API call (pages 60-73)
        
        ...and so on.
        '''
        
        self.recreated = True
        # Attempt to create /raw folder
        try:
            os.mkdir(self.directory + '/raw')
        except OSError:
            self.logger.exception("Folder /raw already exists.")
            exit("Cannot create file structure.")
          
        start_time = time()
        pages_count = 0  
        # Iterate through each entry in the self.pages dict to perform the API calls
        for key in self.pages.keys():
            calls = self.form_call()
            os.mkdir(self.directory + '/raw/' + (str(pages_count)))
            call_count = 0
            for call in calls:
                filename = self.directory + '/raw/' + str(pages_count) + "/" + str(call_count) + ".json"
                with codecs.open(filename, 'w', 'utf-8') as file:
                    text = request.urlopen(call).read().decode('utf-8')
                    file.write(text)
                call_count += 1
            pages_count += 1
        self.logger.debug("Download queries completed in {} seconds."
                          .format(round(time()-start_time, 2)))
        
    def form_call(self):
        '''Form the URLs to pull data from the API. The API supports calls of up to fifty pages
        at a time; if necessary, this will create multiple URLs in case the list of pages is too
        long. Returns a list containing one or more URLs, each of which requests the content of
        1-50 pages.'''
        
        current_page = self.pages.popitem(False)
        self.logger.debug("Requesting content for {}".format(current_page[0]))
        filename = parse.quote(current_page[1].pop(0))
        pages = self.split_calls(current_page[1])

        titles = ""
        api_calls = list()
        for group in pages:
            for number in group:
                self.page_list.append("Page:" + filename + "/" + str(number))
                titles += "Page:" + filename + "/" + str(number) + "|"
            titles = titles[:-1]
            api_calls.append(self.api_json.format(titles))
            titles = ""
        with open('eachpage.pkl', 'wb') as file:
            try:
                pickle.dump(self.page_list, file)
            except Exception as e:
                self.logger.exception("Exception occurred when trying to pickle the attribution "
                                      "page list: {}".format(e.strerror))
        return api_calls
    
    def json_to_text(self):
        os.mkdir(os.curdir + '/text')
        folders = sorted(os.listdir(path=(os.curdir + '/raw')), key=int)
        for folder in folders:
            os.mkdir(os.curdir + '/text/' + folder)
            files = sorted(os.listdir(path=(os.curdir + '/raw/' + folder)), key=lambda x: int(x[0]))
            for file in files:
                with open(os.curdir + '/raw/' + folder + '/' + file, 'r') as f:
                    data = f.read()
                    json_data = json.loads(data)
                    pagedict = dict()
                    for key in json_data["query"]["pages"].keys():
                        pagedict[json_data["query"]["pages"][key]["title"]] = key
                    pagelist = sorted(pagedict.keys())
                    with codecs.open(os.curdir + '/text/' + folder + '/' + file[0] +'.txt', 'w', 'utf-8') as textfile:
                        for pagename in pagelist:
                            textfile.write(json_data["query"]["pages"][pagedict[pagename]]['revisions'][0]["*"])
                            
        
    def organize(self):
        '''Creates the ordered dictionary containing the filenames and page numbers. If possible,
        it uses a pickled version of this pagelist from a previous run to avoid querying the API
        repeatedly. This is mostly for debugging and will probably be removed in the release.'''
        if not os.path.exists('pagelist.pkl'):
            self.logger.debug("No pickled page list found. Querying API.")
            current_url = "/Front matter".encode()
            while current_url != "":
                current_url = parse.quote(current_url)
                
                # Account for relative links
                if current_url[0] == "/":
                    current_url = self.prefix + current_url

                # Create API request    
                current_url = self.api_txt.format(current_url)

                # Get the text of the request
                current_page = request.urlopen(current_url).read().decode('utf-8')
                
                # Search for the link to the next page in the document
                next_r = re.search("\|\snext\s*=\s?[[]{2}(.*?)[]]{2}", current_page)
                if next_r:
                    next_url = next_r.group(1).encode()
                else:
                    next_url = ""
                    
                # Get the nicely-formatted page title    
                title_r = re.search("\[title\]\s=>\s(.*?)\n", current_page)
                if title_r:
                    title = title_r.group(1)     
                    
                # Find each pages index tag and collect the page numbers for each
                pages_r = re.findall("""<pages\sindex="(.*?)"\sfrom=(\d+)\sto=(\d+)\s\/>""",
                                     current_page)
                if pages_r and title:
                    index = pages_r[0][0]
                    if title not in self.pages:
                        self.pages[title] = [index]
                    for page in pages_r:
                        page1 = int(page[1])
                        page2 = int(page[2])
                        if page1 == page2:
                            self.pages[title].append(page1)
                        else:
                            self.pages[title].extend(list(range(page1, page2+1)))
                
                title = None
                current_url = next_url
                
                
            if len(self.pages) == 0:
                raise NoPagesReturned()
                exit()
                
            # Saves to a text file to avoid having to query the API many times
            with open('pagelist.pkl', 'wb') as file:
                try:
                    pickle.dump(self.pages, file)
                except Exception as e:
                    self.logger.exception("Exception occurred when trying to pickle the page list:"
                                          "{}".format(e.strerror))
            
        else:
            self.logger.debug("Page list found. Unpickling.")
            with open('pagelist.pkl', 'rb') as file:
                try:
                    self.pages = pickle.load(file)
                    if len(self.pages) == 0:
                        raise PickleEmpty()
                except PickleEmpty:
                    self.logger.exception("Pickle file is empty. Delete the pagelist.pkl file and"
                                          "try running the program again.")
                    exit()
                except Exception as e:
                    self.logger.exception("Error occurred when trying to unpickle the page list: {}"
                           .format(e.strerror))
            
        self.logger.debug("{} main pages organized.".format(len(self.pages)))
        for page in list(self.pages.items()):
            self.num_pages += len(page[1]) - 1
        
    def split_calls(self,pagelist):
        '''The API only accepts 50 calls at a time, so this function splits the lists of pages
        into groups of 50 or fewer. Because the API sorts results alphabetically, this
        function also splits page numbers <10 or >99 into separate groups to preserve order.
        
        Returns a list of lists of page numbers. Each list of page numbers contains fewer than
        50 pages, and page numbers <10 or >99 get their own list.'''
        splitlist = list()
        low_index, high_index = None, None

        # Find the index of the first number >=10
        for idx,page in enumerate(pagelist):
            if int(page) >= 10:
                low_index = idx
                break
            
        # Find the index of the first number >=100
        for idx,page in enumerate(pagelist):
            if int(page) >= 100:
                high_index = idx
                break
        
        # Split page numbers <10   
        if low_index == None:
            splitlist.append(pagelist)
            return splitlist # The list has no page numbers >=10
        elif low_index > 0:
            splitlist.append(pagelist[:low_index])
            
        # Split page numbers that are >=10 and <100
        if high_index == None:
            top = len(pagelist)
        else:
            top = high_index
            
        number = top-low_index # Number of items in the list containing numbers 10-99
        list_count = ceil(number/50) # Number of sublists needed for this
        first_index = low_index # First index to include in the next list
        for i in range(list_count):
            sublist = list()
            if i == list_count-1:
                page_range = top - first_index
            else:
                page_range = 50
            for j in range(page_range):
                sublist.append(pagelist[first_index+j])
            first_index = first_index + page_range # Update first_index with new index
            splitlist.append(sublist)
            del sublist
        
        # Split page numbers that are >=100        
        if high_index != None:
            number = len(pagelist) - high_index # Number of items containing numbers >=100
            list_count = ceil(number/50) # Number of sublists needed for this
            for i in range(list_count):
                sublist = list()
                if i == list_count-1:
                    page_range = len(pagelist) - first_index
                else:
                    page_range = 50
                for j in range(page_range):
                    sublist.append(pagelist[first_index+j])
                first_index = first_index + page_range
                splitlist.append(sublist)
                del sublist
                
        return splitlist