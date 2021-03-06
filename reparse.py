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

from exceptions import ParseError
import logging, re, util

class Reparser(object):
    def __init__(self):
        self.logger = logging.getLogger("W2L")
        
    def careful_sub(self, text, traverse=False):
        # Currently ignoring {{popup note}} and {{hi}}
        '''Only substitute templates -- passing substituted text through this will not change it.'''
        text = re.sub(r'\{{2}hi\|\dem\|(?P<text>.*?)\}{2}', r'\g<text>', text)
        text = re.sub(r'\{{2}u\|(?P<text>.*?)\}{2}', r'\\uline{\g<text>}', text)
        text = re.sub(r'\{{2}larger\|(?P<text>.*?)\}{2}',
                      r'\\begin{large}\g<text>\\end{large}', text)
        text = re.sub(r'\{{2}x\-smaller\|(?P<text>.*?)\}{2}',
                      r'\\begin{footnotesize}\g<text>\\end{footnotesize}', text)
        text = re.sub(r'\{{2}x\-larger\|(?P<text>.*?)\}{2}',
                      r'\\begin{Large}\g<text>\\end{Large}', text)
        text = re.sub(r"'{3}(?P<text>.*?)'{3}", r'\\textbf{\g<text>}', text)
        text = re.sub(r'[[]{2}(?:(?:.*?)\|)?(?P<link>.*?)[]]{2}', r'\g<link>',
                      text)
        text = re.sub(r'<br\s?/?>', r'\\\\\n', text)
        text = re.sub(r'[{]{2}popup\snote\|(.*?)\|(?P<text>.*?)[}]{2}', r'\g<text>', text)
        text = re.sub(r'\{{2}(?:block\s)?right\|(?P<text>.*?)\}{2}',
                      r'\\begin{flushright}\g<text>\\end{flushright}', text)
        text = text.replace('<u>', '\\uline{').replace('</u>', '}').replace('✓', '{\\checked}')
        text = text.replace("–", "--").replace("—", "---")
        text = text.replace("□", "\\Square~").replace("|", "{\\textbar}")
        if traverse:
            text = text.replace("{", "`").replace("}", "@@")
            text = text.replace("\n", "~")
        return text
        
    def final_sub(self, text):
        '''This can only be run once on text, or it will substitute substitute chars.'''
        text = text.replace("#", "\#").replace("$", "\$").replace("%", "\%")
        text = text.replace("_", "\_").replace("^", "\^").replace("~", "\~")
        text = text.replace("&", "\&")
        return text
    
    def left(self, text):
        offset = None
        o = re.search('\|offset=(?P<o>\d)em', text)
        if o:
            offset = o.group('o')
            ind = text.find('|offset')
            text=text[:ind]
            text = self.sub(text)
            text = "\\hspace*{" + offset + "em}" + text + " \\\\\n"
        return text
    
    def traverse(self, text):
        while True:
            l = util.findall(text, "{{")
            r = util.findall(text, "}}")
            if len(l) < len(r):
                text = text[:-2]
                r.pop()
            elif len(l) == 0:
                break
            else:
                temp = self.careful_sub(text[l[-1]:r[0]+2], True)
                text = text.replace(text[l[-1]:r[0]+2], temp)
        text = text.replace("~", "\n")
        text = self.final_sub(text)
        text = text.replace("`", "{").replace("@@", "}")
        return text
            
    def running_header(self, text):
        '''Parse out the insides of a {{rh}} template into a LaTeX table.'''
        # Remove {{rh and closing }}
        text = text[4:-2]
        # Find indexes of left, right, and center
        breaks = [text.find("|left=") if text.find("|left=") != -1 else None, text.find("|center=")
                  if text.find("|center=") != -1 else None, text.find("|right=") if
                  text.find("|right=") != -1 else None]
        # Break the string into list t containing left, right, and center
        t=list()
        if breaks[0] != None:
            if breaks[1]:
                t.append(text[breaks[0]+6:breaks[1]])
            elif breaks[2]:
                t.append(text[breaks[0]+6:breaks[2]])
            else:
                t.append(text[breaks[0]+6:])
        else:
            t.append(None)
        if breaks[1] != None:
            if breaks[2]:
                t.append(text[breaks[1]+8:breaks[2]])
            else:
                t.append(text[breaks[1]+8:])
        else:
            t.append(None)
        if breaks[2] != None:
            t.append(text[breaks[2]+7:])
        else:
            t.append(None)
        for index in range(3):
            if t[index] != None:
                t[index] = self.sub(t[index])
            else:
                t[index] = ''
        runningheader = ('\n\\hfline{' + t[0] + '}{' + t[1] + '}{'
                         + t[2] + '}\n')
        if "TOP SECRET" in t[2]:
            runningheader = '\n\\vfill\n\\begin{spacing}{0}' + runningheader + '\\end{spacing}\n'
        return runningheader
    
    def sub(self, text):
        '''Perform common substitutions'''
        text = self.careful_sub(text)
        text = self.final_sub(text)
        return text