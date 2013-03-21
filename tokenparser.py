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

import logging, re, wikitable

class Parser(object):
    def __init__(self, outputfile):
        self.logger = logging.getLogger("W2L")
        self.output = outputfile
        self.tell = None
        self.columntell = None
        
    def dispatch(self, t_list):
        for token in t_list:
            self.value = token[1]
            if self.value:
                command = 'self.{0}()'.format(token[0].lower())
                try:
                    exec(command)
                except AttributeError as e:
                    self.logger.debug("No function: {}.".format(e))
                else:
                    self.write(self.value)
                    
    def nested(self, text):
        '''Deal with tokens that may not have been caught because they were nested within other
        tokens (e.g., punctuation in {{center}})'''
        a = re.search('[{]{2}popup\snote\|(.*?)\|', text)
        if a:
            text = text[:a.start()] + text[a.end():]
        b = re.match('[{]{2}x-smaller\|(?P<text>.*?)[}]{2}', text)
        if b:
            text = b.group('text')
            text = "\\footnotesize{" + text + "}"
        text = text.replace("#", "\#").replace("$", "\$").replace("%", "\%").replace("~", "\~")
        text = text.replace("_", "\_").replace("^", "\^").replace("|", "\|").replace("&", "\&")
        return text
                
    def write(self, text):
        if type(text) is str:
            self.output.write(text)
        
#===================================================================================================
# PARSING FUNCTIONS
#===================================================================================================
    # TABLE FUNCTIONS
    def table(self):
        #TODO: TABLE
        pass
    
    def e_table(self):
        #TODO: E_TABLE
        pass
    
    def trow(self):
        #TODO: TROW
        pass
    
    def e_trow(self):
        #TODO: E_TROW
        pass
    
    def titem(self):
        #TODO: TITEM
        pass
    
    def e_titem(self):
        #TODO: E_TITEM
        pass
    
    def tnoinclude(self):
        #TODO: TNOINCLUDE
        pass
    
    def te_noinclude(self):
        #TODO: TE_NOINCLUDE
        pass
    
    def tolist(self):
        #TODO: TOLIST
        pass
    
    def te_olist(self):
        #TODO: TE_OLIST
        pass
    
    def tlitem(self):
        #TODO: TLITEM
        pass
    
    def te_litem(self):
        #TODO: TE_LITEM
        pass
    
    def tforced_whitespace(self):
        #TODO: TFORCED_WHITESPACE
        pass
    
    # WIKITABLE FUNCTIONS
    def wikitable(self):
        self.table = wikitable.Table()
        self.value = ''
    
    def e_wikitable(self):
        self.value = self.table.end()
        del self.table
        
    def tcell(self):
        self.cell = wikitable.Cell(self.table)
        self.value = ''
        
    def e_tcell(self):
        self.value = self.cell.end() # Get the final text of the cell
        self.table.append_cell(self.value) # Add the cell to the table
        self.cell.reset() # Reset cell values for next time
        self.value = ''
        
    def format(self):
        # TODO: Add cellpadding/cellspacing?
        if self.value[0]:                               # Table width
            self.table.set_width(self.value[0])
        if self.value[1]:                               # Text alignment
            self.table.set_alignment(self.value[1])
        if self.value[2]:                               # Border
            self.table.format['border'] = True
            self.table.t['hline'] = '\\hline\n'
        self.value = ''

    def wt_colspan(self):
        self.cell.c_format['colspan'] = self.value
        self.table.format['multicol'] = True
        self.value = ''
        
    def wt_colalign(self):
        self.cell.c_format['center'] = True
        self.value = ''
    
    def wt_boxedcell(self):
        self.cell.c_format['border'] = True
        self.value = ''
                
    def newrow(self):
        self.table.append_row()
        self.value = ''
        
    def cell_contents(self):
        self.cell.append(self.value)
        self.value = ''
        
    # PRE-HTML TOKENS
    def internallink(self):
        #TODO: INTERNAL LINK
        pass
    
    def pagequality(self):
        if self.output.tell() != 0:
            self.value = "\n\\newpage\n"
        else:
            self.value = ""
    
    def declassified(self):
        self.value = ("\\begin{spacing}{0.7}\n\\begin{center}\n\\begin{scriptsize}\\textbf" 
        "{Declassified} per Executive Order 13526, Section 3.3\\\\NND Project Number: NND 63316." 
        "By: NWD Date: 2011\n\\end{scriptsize}\n\\end{center}\n\\end{spacing}\n")
    
    def secret(self):
        #TODO: SECRET
        pass
        
    def runhead(self):
        #TODO: RUNHEAD
        pass
    
    # HTML TOKENS
    def olist(self):
        '''Begin ordered list.'''
        self.value = '\\begin{enumerate}'
    
    def e_olist(self):
        '''End ordered list.'''
        self.value = '\\end{enumerate}'
    
    def litem(self):
        '''Format list item.'''
        self.value = "\item " + self.value
        
    def e_litem(self):
        '''Do nothing.'''
        self.value = ""
        
    def noinclude(self):
        #TODO: NOINCLUDE
        self.value = ""
        pass
    
    def e_noinclude(self):
        #TODO: E_NOINCLUDE
        self.value = ""
        pass
    
    def reflist(self):
        #TODO: REFLIST
        pass
    
    def ref(self):
        #TODO: REF
        pass
    
    def e_ref(self):
        #TODO: E_REF
        pass
    
    def forced_whitespace(self):
        '''Add whitespace.'''
        try: 
            self.output.seek(-1, 1)
            preceding = self.output.read(1)
            if preceding != "\n" and preceding != "}":
                self.value = '\\\\\n'
            else:
                self.value = ''
        except:
            pass
    
    # CENTERED TOKENS
    def centered(self):
        '''Begin centered text.'''
        # TODO: Check that there is a '\\' before and after centered text
        self.value = "\\begin{center}\n"
    
    def e_centered(self):
        '''End centered text.'''
        self.output.seek(-1, 1)
        preceding = self.output.read(1)
        if preceding == "\n":
            self.value = "\\end{center}\n"
        else:
            self.value = "\n\\end{center}\n"
          
    def right(self):
        '''Begin right-aligned text.'''
        # TODO: Check that there is a '\\' before and after centered text
        self.value = "\\begin{flushright}\n"
    
    def e_right(self):
        '''End centered text.'''
        self.output.seek(-1, 1)
        preceding = self.output.read(1)
        if preceding == "\n":
            self.value = "\\end{flushright}\n"
        else:
            self.value = "\n\\end{flushright}\n"  
    
    
    # POST-HTML TOKENS
    def pspace(self):
        '''Replace {{nop}} with \\.'''
        try: 
            self.output.seek(-1, 1)
            preceding = self.output.read(1)
            if preceding != "\n" and preceding != "}":
                self.value = '\\\\\n'
            else:
                self.value = ''
        except:
            pass
        
    def cindent(self):
        # TODO: CONTINUE INDENT FROM PREVIOUS PAGE
        pass
    
    def indent(self):
        # TODO: BLOCK INDENT
        pass
    
    def pagenum(self):
        # TODO: PAGE NUMBER
        pass
    
    def pent(self):
        # TODO: NOTE
        pass
    
    def popup(self):
        self.value = self.nested(self.value)
        
    def size(self):
        '''Adjust the size of the text.'''
        self.value = ("\\begin{" + self.value[0] + "}\n" + self.nested(self.value[1]) +
                      " \\\\\n\\end{" + self.value[0] + "}\n")
        pass
        
    def underlined(self):
        '''Replace underlined text with italicized text.'''
        self.italicized()
        
    def bolded(self):
        '''Bold text.'''
        self.value = "\\textbf{" + self.value + "}"
    
    def italicized(self):
        '''Italicize text.'''
        self.value = "\\textit{" + self.value + "}"
        
    def wlink(self):
        '''Print only the display text of the wikilink.'''
        pass
    
    def rule(self):
        '''Horizontal rule.'''
        self.value = "\n\\rule{\\textwidth}{2px} \\\\\n\n"
    
    # BASIC TOKENS
    def ellipses(self):
        '''Convert to proper ellipsis formatting.'''
        if self.value == "...":
            self.value = "\\ldots"
        else:
            self.value = "\\ldots."
            
    def checkbox_empty(self):
        self.value = "\\Square~"
    
    def checkbox_checked(self):
        self.value = "\\CheckedBox~"
        pass
    
    def punct(self):
        # TODO: Figure out `` and " for quotes
        '''Write punctuation to file, escaping any characters with special functions in LaTeX.'''
        escape = ["#", "$", "%", "&", "_", "\\"]
        if self.value in escape: # Precede the punctuation with a backslash
            self.value = "\\" + self.value
        elif self.value == "°": # Replace degree symbol
            self.value = "\\degree"
        elif self.value == "–": # Replace en dash
            self.value = "--"
        elif self.value == "—": # Replace em dash
            self.value = "---"
        elif self.value == "\|": # Replace pipe
            self.value = "\\textbar"
        elif self.value == "}":
            self.value = ""
        elif self.value == "{":
            self.value = ""
        
    
    def word(self):
        # TODO: Fix large spaces after abbreviations (i.e., e.g., etc.)
        '''Write word to file, using compose codes for any accented characters.'''
        if "é" in self.value:
            self.value = self.value.replace("é", "\\'{e}")
        
    def number(self):
        '''Write number(s) to file without changing anything.'''
        pass
        
    def whitespace(self):
        '''Replace newlines with '\\', replace tabs with spaces, leave spaces the same.''' 
        if '\r' in self.value or '\n' in self.value:
            try: 
                self.output.seek(-1, 1)
                preceding = self.output.read(1)
                if preceding != "\n" and preceding != "}":
                    self.value = '\\\\\n'
                else:
                    self.value = ''
            except:
                pass
        else:
            self.value = ' '