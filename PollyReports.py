# PollyReports
# Copyright &copy; 2012 Chris Gonnerman
# All rights reserved.
#
# Software License
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# Neither the name of the author nor the names of any contributors
# may be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# AUTHOR OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
    PollyReports.py

    PollyReports provides a framework for report generation.

    A Report object has a data source bound to it at instantiation.
    One or more Band objects (at least, a detail Band) must be added
    to it, and then the generate() method will be called to process
    the data source (an iterator that produces objects that can be
    accessed via [] operations, meaning mainly dict, list, and tuple
    types), executing the detail Band once for each row and producing
    a PDF containing the output.

    Band objects contain a list of Elements (generally at least one)
    which define how data from the row should be printed.  An Element
    may print any normal data item or label and may be subclassed
    to handle other things like images.
"""




class Renderer:

    def __init__(self, pos, font, text, right, height):
        self.pos = pos
        self.font = font
        self.text = text
        self.right = right
        self.height = height

    def render(self, offset, canvas):
        canvas.setFont(*self.font)
        if self.right:
            canvas.drawRightString(self.pos[0], (-1) * (self.pos[1]+offset+self.font[1]), self.text)
        else:
            canvas.drawString(self.pos[0], (-1) * (self.pos[1]+offset+self.font[1]), self.text)

    def applyoffset(self, offset):
        self.pos = (self.pos[0], self.pos[1] + offset)
        return self


class Element:

    # text refers to a label;
    # key is a value used to look up data in the record;
    # getvalue is a function that accepts the row as a parameter
    #   and returns text to print.
    # all three should not be submitted at the same time,
    #   but if they are, getvalue overrides key overrides text.

    def __init__(self, pos, font,
                 text = None, key = None, getvalue = None,
                 right = 0, format = str, leading = None):
        self.text = text
        self.key = key
        self._getvalue = getvalue
        self.pos = pos
        self.font = font
        self._format = format
        self.right = right
        if leading is not None:
            self.leading = leading
        else:
            self.leading = max(1, int(font[1] * 0.4 + 0.5))
        self.summary = 0 # used in SumElement, below

    def gettext(self, row):
        return self._format(self.getvalue(row))

    def getvalue(self, row):
        if self._getvalue is not None:
            return self._getvalue(row)
        if self.key is not None:
            return row[self.key]
        if self.text is not None:
            return self.text
        return "???"

    # generating an element returns a Renderer object
    # which can be used to print the element out.

    def generate(self, row):
        return Renderer(self.pos, self.font, self.gettext(row), self.right,
            self.font[1] + self.leading)


class SumElement(Element):

    def getvalue(self, row):
        rc = self.summary
        self.summary = 0
        return rc

    def summarize(self, row):
        self.summary += Element.getvalue(self, row)


class Rule:

    def __init__(self, pos, width, thickness = 1):
        self.pos = pos
        self.width = width
        self.height = thickness

    def gettext(self, row):
        return "-"

    def getvalue(self, row):
        return "-"

    def generate(self, row):
        return self

    def render(self, offset, canvas):
        canvas.saveState()
        canvas.setLineWidth(self.height)
        canvas.setStrokeGray(0)
        canvas.line(self.pos[0],            -1 * (self.pos[1]+offset),
                    self.pos[0]+self.width, -1 * (self.pos[1]+offset))
        canvas.restoreState()


class Band:

    # key, getvalue and previousvalue are used only for group headers and footers
    # newpagebefore/after do not apply to detail bands, page headers, or page footers, obviously
    # newpageafter also does not apply to the report footer

    def __init__(self, elements = None, childbands = None, 
                 key = None, getvalue = None, 
                 newpagebefore = 0, newpageafter = 0):
        self.elements = elements
        self.key = key
        self._getvalue = getvalue
        self.previousvalue = None
        self.newpagebefore = newpagebefore
        self.newpageafter = newpageafter
        if childbands is None:
            self.childbands = []
        else:
            self.childbands = childbands

    # generating a band creates a list of Renderer objects.
    # the first element of the list is a single integer
    # representing the calculated printing height of the
    # list.

    def generate(self, row):
        elementlist = [ 0 ]
        for element in self.elements:
            renderer = element.generate(row)
            elementlist[0] = max(elementlist[0], renderer.height + renderer.pos[1])
            elementlist.append(renderer)
        for band in self.childbands:
            childlist = band.generate(row)
            for renderer in childlist[1:]:
                renderer.applyoffset(elementlist[0])
                elementlist.append(renderer)
            elementlist[0] += childlist[0]
        return elementlist

    # summarize() is only used for total bands, i.e. group and
    # report footers.

    def summarize(self, row):
        for element in self.elements:
            if hasattr(element, "summarize"):
                element.summarize(row)

    # these methods are used only in group headers and footers

    def getvalue(self, row):
        if self._getvalue is not None:
            return self._getvalue(row)
        if self.key is not None:
            return row[self.key]
        return 0

    def ischanged(self, row):
        pv = self.previousvalue
        self.previousvalue = self.getvalue(row)
        if pv is not None and pv != self.getvalue(row):
            return 1
        return None


class Report:

    def __init__(self, datasource):
        self.datasource = datasource
        self.pagesize = None
        self.topmargin = 36
        self.bottommargin = 36

        # bands
        self.detailband = None
        self.pageheader = None
        self.pagefooter = None
        self.reportfooter = None
        self.groupheaders = []
        self.groupfooters = []

    def newpage(self, canvas, row, pagenumber):
        if pagenumber:
            canvas.showPage()
        self.endofpage = self.pagesize[1] - self.bottommargin
        canvas.translate(0, self.pagesize[1])
        self.current_offset = self.topmargin
        if self.pageheader:
            elementlist = self.pageheader.generate(row)
            self.current_offset += self.addtopage(canvas, elementlist)
        if self.pagefooter:
            elementlist = self.pagefooter.generate(row)
            self.endofpage = self.pagesize[1] - self.bottommargin - elementlist[0]
            for el in elementlist[1:]:
                el.render(self.endofpage, canvas)
        return pagenumber + 1

    def addtopage(self, canvas, elementlist):
        for el in elementlist[1:]:
            el.render(self.current_offset, canvas)
        return elementlist[0]

    def generate(self, canvas):
        self.pagesize = (int(canvas._pagesize[0]), int(canvas._pagesize[1]))
        self.current_offset = self.pagesize[1]
        pagenumber = 0
        self.endofpage = self.pagesize[1] - self.bottommargin
        prevrow = None
        firstrow = 1

        for row in self.datasource:

            if firstrow:
                firstrow = None
                for band in self.groupheaders:
                    elementlist = band.generate(row)
                    if (self.current_offset + elementlist[0]) >= self.endofpage:
                        pagenumber = self.newpage(canvas, row, pagenumber)
                    self.current_offset += self.addtopage(canvas, elementlist)

            firstchanged = None
            for i in range(len(self.groupfooters)):
                if self.groupfooters[i].ischanged(row):
                    if firstchanged is None:
                        firstchanged = i
            if firstchanged is not None:
                for i in range(firstchanged, len(self.groupfooters)):
                    elementlist = self.groupfooters[i].generate(prevrow)
                    if self.groupfooters[i].newpagebefore or (self.current_offset + elementlist[0]) >= self.endofpage:
                        pagenumber = self.newpage(canvas, row, pagenumber)
                    self.current_offset += self.addtopage(canvas, elementlist)
                    if self.groupfooters[i].newpageafter:
                        self.current_offset = self.pagesize[1]
            for band in self.groupfooters:
                band.summarize(row)

            lastchanged = None
            for i in range(len(self.groupheaders)):
                if self.groupheaders[i].ischanged(row):
                    lastchanged = i
            if lastchanged is not None:
                for i in range(lastchanged+1):
                    elementlist = self.groupheaders[i].generate(row)
                    if self.groupheaders[i].newpagebefore or (self.current_offset + elementlist[0]) >= self.endofpage:
                        pagenumber = self.newpage(canvas, row, pagenumber)
                    self.current_offset += self.addtopage(canvas, elementlist)
                    if self.groupheaders[i].newpageafter:
                        self.current_offset = self.pagesize[1]

            elementlist = self.detailband.generate(row)
            if (self.current_offset + elementlist[0]) >= self.endofpage:
                pagenumber = self.newpage(canvas, row, pagenumber)
            self.current_offset += self.addtopage(canvas, elementlist)
            if self.reportfooter:
                self.reportfooter.summarize(row)
            prevrow = row

        for band in self.groupfooters:
            elementlist = band.generate(prevrow)
            if band.newpagebefore or (self.current_offset + elementlist[0]) >= self.endofpage:
                pagenumber = self.newpage(canvas, row, pagenumber)
            self.current_offset += self.addtopage(canvas, elementlist)
            if band.newpageafter:
                self.current_offset = self.pagesize[1]

        if self.reportfooter:
            elementlist = self.reportfooter.generate(row)
            if self.reportfooter.newpagebefore or (self.current_offset + elementlist[0]) >= self.endofpage:
                pagenumber = self.newpage(canvas, row, pagenumber)
            self.current_offset += self.addtopage(canvas, elementlist)

        canvas.showPage()


if __name__ == "__main__":

    from reportlab.pdfgen.canvas import Canvas
    from testdata import data

    rpt = Report(data)
    rpt.detailband = Band([
        Element((36, 0), ("Helvetica", 11), key = "name"),
        Element((400, 0), ("Helvetica", 11), key = "amount", right = 1),
    ], childbands = [
        Band([
            Element((72, 0), ("Helvetica", 11), key = "phone"),
        ]),
    ])
    rpt.pageheader = Band([
        Element((36, 0), ("Times-Bold", 20), text = "Page Header"),
        Element((36, 24), ("Helvetica", 12), text = "Name"),
        Element((400, 24), ("Helvetica", 12), text = "Amount", right = 1),
        Rule((36, 42), 7.5*72),
    ])
    rpt.pagefooter = Band([
        Element((72*8, 0), ("Times-Bold", 20), text = "Page Footer", right = 1),
    ])
    rpt.reportfooter = Band([
        Rule((330, 4), 72),
        Element((240, 4), ("Helvetica-Bold", 12), text = "Grand Total"),
        SumElement((400, 4), ("Helvetica-Bold", 12), key = "amount", right = 1),
        Element((36, 16), ("Helvetica-Bold", 12), text = ""),
    ])
    rpt.groupfooters = [
        Band([
            Rule((330, 4), 72),
            Element((36, 4), ("Helvetica-Bold", 12), getvalue = lambda x: x["name"][0].upper(),
                format = lambda x: "Subtotal for %s" % x),
            SumElement((400, 4), ("Helvetica-Bold", 12), key = "amount", right = 1),
            Element((36, 16), ("Helvetica-Bold", 12), text = ""),
        ], getvalue = lambda x: x["name"][0].upper(), newpageafter = 1),
    ]
    rpt.groupheaders = [
        Band([
            Rule((36, 20), 7.5*72),
            Element((36, 4), ("Helvetica-Bold", 12), getvalue = lambda x: x["name"][0].upper(),
                format = lambda x: "Names beginning with %s" % x),
        ], getvalue = lambda x: x["name"][0].upper()),
    ]

    canvas = Canvas("test.pdf", (72*11, 72*8.5))
    rpt.generate(canvas)
    canvas.save()


# end of file.
