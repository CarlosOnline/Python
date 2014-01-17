import collections
import datetime
import os
import platform
import re
import sys
import threading
import time

from   Utility.Utility import *

# def print(*args):
#     argsMessage = []
#     for item in args:
#         argsMessage.append(str(item))
#     Log(' '.join(argsMessage), ConsoleColor=Fore.RED)

TurnOnHtmlDebugging = False

def trace(*args):
    if TurnOnHtmlDebugging:
        argsMessage = [item for item in args]
        Log(' '.join(argsMessage), ConsoleColor=Fore.CYAN)

def make_tag(name, attribs = None):
    tag = DictN({'name' : name})
    tag.name = name
    tag.attribs = attribs
    tag.anonymous = ternary(name in HTML.Anonymous, True, False)
    tag.leaf = ternary(name in HTML.Leaf, True, False)
    return tag

example = {
    'head': {
        'title' : 'hi',
        'style' : {
            'type' : '"text/css"',
            'span' : """
                br {
                    clear: both;
                }
            """,
        }
    },
    'body' : {
        'h1' : 'Header',
        'table' : {
            'id' : 'th_and_content',
            'th' : [
                "column1",
                "column2",
                {
                    'style' : '"display:none;"',
                    'b' : "column3",
                },
                "column4",
            ],
            'content' : [
                "column1",
                "column2",
                {
                    'style' : '"display:none;"',
                    'b' : "column3",
                },
                "column4",
            ],
        }
    }
}

"""

"""
class HTML():

    Tags = [
        'b',
        'body',
        'br',
        'content',
        'div',
        'i',
        'h1',
        'h2',
        'h3',
        'h4',
        'head',
        'hr',
        'html',
        'li',
        'span',
        'style',
        'table',
        'td',
        'th',
        'tr',
        'title',
        'ul',
    ]

    NextTagMap = {
        'table' : {'name' : 'tr' },
        'tr' : [
                    {
                        'key' : 'td',
                        'tag' : {'name' : 'td' }
                    },
                    {
                        'key' : 'th',
                        'tag' : {'name' : 'th' }
                    },
                ],
    }

    Anonymous = [
        'li',
        'tr',
        'th',
        'td',
    ]

    Leaf = [
        'li',
        'th',
        'td',
    ]

    Parented = {
        'style' : 'head',
    }

    def __init__(self, OutputFile):
        self.html = []
        self.indent = -3
        self.outputFile = ExpandPath(OutputFile)
        self.stack = []

    def get_container_tag(self, tag):

        if tag.name == 'th':
            previousTag = self.stack[-1]
            if previousTag.name == 'table':
                return self.tag('tr')
        else:
            return tag

    def get_next_tag(self, data, tagList = None):
        if not tagList:
            tagList = HTML.Tags

        if isinstance(data, dict):
            for key, value in data.items():
                #print(key, value)
                if self.is_tag(key) and key in tagList:
                    return make_tag(key)
                elif isinstance(value, dict) or isinstance(value, list):
                    next = self.get_next_tag(value, tagList)
                    if next:
                        return next
        elif isinstance(data, list):
            for key in data:
                #print(key)
                if isinstance(key, dict) or isinstance(key, list):
                    next = self.get_next_tag(key, tagList)
                    if next:
                        return next
                elif self.is_tag(key) and key in tagList:
                    return make_tag(key)

        return None

    def get_nested_tag(self, tag, data=None):
        #trace(tag, data)
        if tag.name in HTML.NextTagMap:
            node = HTML.NextTagMap[tag.name]
            #print('node', node)
            if isinstance(node, list):
                matches = [ item['key'] for item in node]
                #print(matches)
                next = self.get_next_tag(data, matches)
                if not next:
                    next = node[0]['tag']

                trace(next)
                return make_tag(next['name'])

            trace(node['name'])
            return make_tag(node['name'])

        if not tag.anonymous:
            trace('Not Anonymous')
            return None

        trace(tag)
        return tag

    def is_tag(self, name):
        if name not in HTML.Tags:
            return False

        if name in HTML.Parented.keys():
            parent = HTML.Parented[name]
            parented = parent in [ tag.name for tag in self.stack ]
            return parented

        return True

    def get_attribs(self, tag, data):

        attribs = []
        if isinstance(data, dict):
            # get attributes
            for key in data:
                if not self.is_tag(key):
                    #Log('attribute: {0} = "{1}"'.format(key, data[key]))
                    attribs.append('{0} = "{1}"'.format(key, data[key]))

        if len(attribs):
            attribs.insert(0, ' ')
        return attribs

    def write(self, html):
        indent = Globals.Indent
        Globals.Indent = 0
        FileLog(html, Indent=self.indent, FilePath=self.outputFile, Verbose=False, ConsoleColor=Fore.CYAN)
        Globals.Indent = indent

    def encode_tag(self, tag, data = {}, encoder=None, OpenOnly=False):

        if len(self.stack) and self.stack[-1].name == tag.name:
            Error('duplicate stack entry')

        self.stack.append(tag)
        trace('stack-start', [ item.name for item in self.stack])

        self.indent += 3

        if tag.attribs == None:
            tag.attribs = self.get_attribs(tag, data)
        attribs = tag.attribs
        if tag.anonymous and isinstance(data, dict):
            attribs.extend(self.get_attribs(tag, data))
        attribs = ' '.join(attribs)

        tag.written = True
        popStack = True

        if OpenOnly:
            self.write('<{0}{1}>'.format(tag.name, attribs))
            return
        elif encoder:
            self.write('<{0}{1}>'.format(tag.name, attribs))
            encoder(tag, data)
            if tag in self.stack:
                self.write('</{0}>'.format(tag.name))
            else:
                popStack = False
        else:
            self.write('<{0}{1}>{2}</{0}>'.format(tag.name, attribs, str(data)))

        self.indent -= 3
        if popStack:
            self.stack.pop()
        trace('stack-end', [ item.name for item in self.stack])

    def encode_endtag(self, tag):
        self.write('</{0}>'.format(tag.name))
        self.indent -= 3
        self.stack.pop()
        trace('stack', [ item.name for item in self.stack])

    def encode(self, tag, data):
        trace(tag)
        trace('data:', data)

        def get_encoder():

            writable = tag.name != 'content'

            if not self.is_tag(tag.name):
                Error('Invalid tag [tag]')
            elif isinstance(data, dict):
                return [ not tag.leaf, self.encode_dict ]
            elif isinstance(data, list):
                return [ not tag.leaf, self.encode_list ]
            elif tag.name == 'table':
                return [ writable, self.encode_table ]
            elif tag.name == 'tr':
                return [ writable, self.encode_tr ]
            # elif tag.name == 'th':
            #    return [ True, self.encode_th ]
            elif tag.name == 'content':
                return [ False, self.encode_content ]
            else:
                return [ True, None ]

        write, encoder = get_encoder()

        if tag.name and not tag.written and write:
            self.encode_tag(tag, data, encoder)

        elif encoder:
            encoder(tag, data)
        else:
            self.write(str(data))

    def encode_table(self, tag, data):
        trace(tag, data)

        for item in data:
            self.encode(make_tag('tr'), item)

    def encode_tr(self, tag, data):
        trace(tag, data)

        for item in data:
            self.encode(make_tag('th'), item)

    def encode_th(self, tag, data):
        trace(tag, data)

        if isinstance(data, list) or isinstance(data, dict):
            for item in data:
                self.encode(make_tag('th'), item)
        else:
            self.write(str(data))

    def encode_list(self, tag, data):
        trace(tag, data)

        for item in data:
            nested = self.get_nested_tag(tag, item)
            if nested and nested.leaf and not tag.leaf and not tag.written:
                self.encode_tag(tag, data, OpenOnly=True)

            if nested:
                self.encode(make_tag(nested.name, nested.attribs), item)
            else:
                self.encode(tag, item)

            if nested and nested.leaf and not tag.leaf:
                self.encode_endtag(tag)
                tag.written = False

    def encode_dict(self, tag, data):
        trace(tag, data)

        if not tag.attribs:
            tag.attribs = []
        tag.attribs.extend(self.get_attribs(tag, data))

        writeTag = False

        for key, value in data.items():
            next = make_tag(key)
            if key == 'content':
                newNext = self.get_nested_tag(tag)
                if newNext:
                    next = newNext

            if self.is_tag(key):
                # check if going from leaf to nested tags
                if tag.leaf and tag.name != next.name:
                    self.encode_tag(tag, data, OpenOnly=True)
                    self.encode(next, value)
                    self.encode_endtag(tag)
                else:
                    self.encode(next, value)
            else:
                trace('Skipping attribute [key] : [value]')

    def encode_content(self, tag, data):
        trace(tag, data)

        if isinstance(data, dict):
            Error('content tag is not simple type')
        else:
            self.write(data)

    def encode_simple(self, tag, data):
        trace(tag, data)

        self.write(str(data))

    @staticmethod
    def encode_to_file(Data, OutputFile):
        OutputFile = ExpandPath(OutputFile)
        Trace(OutputFile)

        if os.path.exists(OutputFile):
            DeleteFile(OutputFile)

        html = HTML(OutputFile)
        for key, value in Data.items():
            html.encode(make_tag(key), value)

        #fp = open(OutputFile, 'w')
        #fp.write('\n'.join(html.html))
        #fp.close()

        Log('Generated [OutputFile]')
