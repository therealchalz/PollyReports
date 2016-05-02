#coding=utf-8

# PollyReports
# Copyright 2012-2015 Chris Gonnerman
# All rights reserved.
#
# BSD 2-Clause License
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.  Redistributions in binary
# form must reproduce the above copyright notice, this list of conditions and
# the following disclaimer in the documentation and/or other materials provided
# with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###############################################################################
# Thanks to Jose Jachuf, who provided the titleband implementation and
# the initial version of the Image class, and who implemented Unicode support.

from reportlab.lib.utils import simpleSplit


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


class BaseRenderer(object):
    def __init__(self, parent=None, pos=None, onrender=None):
        self.parent = parent
        self.pos = pos or (0,0)
        self.onrender = onrender
        
    def render(self, offset, canvas):
        if self.onrender is not None:
            self.onrender(self)

    def applyoffset(self, offset):
        self.pos = (self.pos[0], self.pos[1] + offset)
        return self

class TextRenderer(BaseRenderer):

    def __init__(self, font, text, align, height, width, **kwargs):
        BaseRenderer.__init__(self, **kwargs)
        self.font = font
        self.align = align
        self.lineheight = height
        self.width = width

        if self.width is None:
            self.lines = text.split("\n")
        else:
            self.lines = simpleSplit(text, *self.font, maxWidth=self.width)

        self.height = height * len(self.lines)

    def render(self, offset, canvas):
        BaseRenderer.render(self, offset, canvas)

        leftmargin = self.parent.report.leftmargin
        canvas.setFont(*self.font)
        for text in self.lines:
            if "right".startswith(self.align):
                canvas.drawRightString(
                    self.pos[0]+leftmargin,
                    (-1) * (self.pos[1]+offset+self.font[1]),
                    text)
            elif "center".startswith(self.align) or "centre".startswith(self.align):
                canvas.drawCentredString(
                    self.pos[0]+leftmargin,
                    (-1) * (self.pos[1]+offset+self.font[1]),
                    text)
            elif "left".startswith(self.align):
                canvas.drawString(
                    self.pos[0]+leftmargin,
                    (-1) * (self.pos[1]+offset+self.font[1]),
                    text)
            elif "align".startswith(self.align):
                canvas.drawAlignedString(
                    self.pos[0]+leftmargin,
                    (-1) * (self.pos[1]+offset+self.font[1]),
                    text)
            offset += self.lineheight

class BaseElement(object):

    def __init__(self, pos=None, onrender = None):
        self.pos = pos or (0,0)
        self.onrender = onrender


class TextElement(BaseElement):

    text_conversion = str

    # text refers to a label;
    # key is a value used to look up data in the record;
    # getvalue is a function that accepts the row as a parameter
    #   and returns text to print.
    # all three should not be submitted at the same time,
    #   but if they are, getvalue overrides key overrides text.

    def __init__(self, pos, font, text = None,
                 key = None, getvalue = None, sysvar = None,
                 align = "left", format = str, width = None,
                 leading = None, **kwargs):
        BaseElement.__init__(self, pos, **kwargs)
        self.text = text
        self.key = key
        self._getvalue = getvalue
        self.sysvar = sysvar
        self.font = font
        self._format = format
        self.align = align
        self.width = width
        if leading is not None:
            self.leading = leading
        else:
            self.leading = max(1, int(font[1] * 0.4 + 0.5))

        self.report = None
        self.summary = 0 # used in SumElement, below

    def gettext(self, row):
        value = self.getvalue(row)
        if value is None:
            return ""
        return self._format(value)

    # prior to 1.6.7, self.text was returned blindly;
    # Jose Jachuf changed the behavior to encode as
    # utf8.  this evidently broke other people's code,
    # particularly in Python 3.  starting in 1.7.7,
    # a class variable text_conversion (found above,
    # initialized to str) determines how self.text
    # is returned.  those wanting Jose's defined
    # behavior should do this:
    #
    #   import PollyReports
    #   PollyReports.Element.text_conversion = \
    #       lambda x: x.encode('utf8')
    #
    # thus restoring unicode-agnosticism to this module.

    def getvalue(self, row):
        if self._getvalue is not None:
            return self._getvalue(row)
        if self.key is not None:
            return (TextElement.text_conversion(self.text) if self.text is not None else "") + (row[self.key] if row[self.key] is not None else "")
        if self.text is not None:
            return TextElement.text_conversion(self.text)
        if self.sysvar is not None:
            return getattr(self.report, self.sysvar)
        return None

    # generating an element returns a Renderer object
    # which can be used to print the element out.

    def generate(self, row):
        return TextRenderer(self.font, self.gettext(row), self.align,
            self.font[1] + self.leading, self.width, pos=self.pos, parent=self)


class SumElement(TextElement):

    def getvalue(self, row):
        rc = self.summary
        self.summary = 0
        return rc

    def summarize(self, row):
        v = Element.getvalue(self, row)
        if v is None:
            v = 0
        self.summary += v

class ShapeRenderer(BaseRenderer):
        
    def __init__(self, height, width, shape, colors, fill, stroke, **kwargs):
        BaseRenderer.__init__(self, **kwargs)
        self.height = height
        self.width = width
        self.shape = shape
        self.colors = colors
        self.fill = fill
        self.stroke = stroke

    def render(self, offset, canvas):
        BaseRenderer.render(self, offset, canvas)
        
        leftmargin = self.parent.report.leftmargin
        canvas.saveState()
        if self.colors is not None:
            canvas.setFillColor(self.colors[(self.parent.report.rownumber-1) % len(self.colors)])
        if self.shape == "rectangle":
            canvas.rect(self.pos[0]+leftmargin,
                    (-1) * (self.pos[1]+offset+self.height),
                    self.width,
                    self.height,
                    fill=self.fill,
                    stroke=self.stroke)
        elif self.shape == "line":
            canvas.line(self.pos[0]+leftmargin,
                    (-1) * (self.pos[1]+offset),
                    self.pos[0]+leftmargin+self.width,
                    (-1) * (self.pos[1]+offset+self.height))
        canvas.restoreState()
class ShapeElement(BaseElement):
    
    def __init__(self, pos, shape, width, height=0, colors=None, bottomMargin=0, fill=True, stroke=True, **kwargs):
        BaseElement.__init__(self, pos, **kwargs)
        if shape in ["rectangle", "line"]:
            self.shape = shape
        #else:
            #TODO: error
        self.height = height
        self.width = width
        self.colors = colors
        self.fill = fill
        self.stroke = stroke
        self.bottomMargin = bottomMargin
        
    def generate(self, row):
        return ShapeRenderer(pos=self.pos, height=self.height,
                 onrender=self.onrender, width=self.width, shape=self.shape,
                 colors=self.colors, fill=self.fill, stroke=self.stroke, parent=self)

class Rule(object):

    def __init__(self, pos, width, thickness = 1, report = None):
        self.pos = pos
        self.width = width
        self.height = thickness
        self.report = report

    def gettext(self, row):
        return "-"

    def getvalue(self, row):
        return "-"

    def generate(self, row):
        return Rule(self.pos, self.width, self.height, self.report)

    def render(self, offset, canvas):
        leftmargin = self.report.leftmargin
        canvas.saveState()
        canvas.setLineWidth(self.height)
        canvas.setStrokeGray(0)
        canvas.line(self.pos[0]+leftmargin,
                    -1 * (self.pos[1]+offset+self.height/2),
                    self.pos[0]+self.width+leftmargin,
                    -1 * (self.pos[1]+offset+self.height/2))
        canvas.restoreState()

    def applyoffset(self, offset):
        self.pos = (self.pos[0], self.pos[1] + offset)
        return self


class ImageRenderer(object):

    def __init__(self, parent, pos, width, height, text, onrender):
        self.parent = parent
        self.pos = pos
        self.width = width
        self.height = height
        self.text = text
        self.onrender = onrender

    def render(self, offset, canvas):
        if self.onrender is not None:
            self.onrender(self)
        leftmargin = self.parent.report.leftmargin
        canvas.drawImage(self.text,
                self.pos[0] + leftmargin,
                -1 * (self.pos[1]+self.height+offset),
                width = self.width,
                height = self.height,
                mask = "auto")

    def applyoffset(self, offset):
        self.pos = (self.pos[0], self.pos[1] + offset)
        return self


class Image(object):

    def __init__(self, pos = None, width = None, height = None,
                 text = None, key = None, getvalue = None,
                 onrender = None):
        self.pos = pos
        self.width = width
        self.height = height
        self.text = text
        self.key = key
        self._getvalue = getvalue
        self.onrender = onrender

        self.report = None

    def gettext(self, row):
        return self.getvalue(row)

    def getvalue(self, row):
        if self._getvalue is not None:
            return self._getvalue(row)
        if self.key is not None:
            return row[self.key]
        if self.text is not None:
            return self.text
        return ""

    def generate(self, row):
        return ImageRenderer(self, self.pos, self.width, self.height,
            self.gettext(row), self.onrender)


class Band(object):

    # key, getvalue and previousvalue are used only for group headers and footers
    # newpagebefore/after do not apply to detail bands, page headers, or page footers, obviously
    # newpageafter also does not apply to the report footer

    def __init__(self, elements = None, childbands = None,
                 additionalbands = None, key = None, getvalue = None,
                 newpagebefore = 0, newpageafter = 0, backgrounds = None):
        self.elements = elements
        self.key = key
        self._getvalue = getvalue
        self.previousvalue = None
        self.newpagebefore = newpagebefore
        self.newpageafter = newpageafter
        self.childbands = childbands or []
        self.additionalbands = additionalbands or []
        self.backgrounds = backgrounds or []

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
        if len(self.backgrounds) > 0:
            numBackgrounds = 1
            for background in self.backgrounds:
                background.height = elementlist[0]-background.pos[1]-background.bottomMargin
                renderer = background.generate(row)
                elementlist.insert(numBackgrounds,renderer) # render backgrounds first, in order
                numBackgrounds += 1
        return elementlist

    # summarize() is only used for total bands, i.e. group and
    # report footers.

    def summarize(self, row):
        for element in self.elements:
            if hasattr(element, "summarize"):
                element.summarize(row)
        for band in self.childbands:
            band.summarize(row)
        for band in self.additionalbands:
            band.summarize(row)

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


class Report(object):

    def __init__(self, datasource = None,
            titleband = None, detailband = None,
            pageheader = None, pagefooter = None,
            reportheader = None, reportfooter = None,
            groupheaders = None, groupfooters = None):
        self.datasource = datasource
        self.pagesize = None
        self.topmargin = 36
        self.bottommargin = 36
        self.leftmargin = 36

        # bands
        self.titleband = titleband
        self.detailband = detailband
        self.pageheader = pageheader
        self.pagefooter = pagefooter
        self.reportfooter = reportfooter
        self.reportheader = reportheader
        self.groupheaders = groupheaders or []
        self.groupfooters = groupfooters or []

        self.pagenumber = 0
        self.rownumber = 0

        self.rowfunc = None

        # private
        self._sum_detail_ht = 0
        self._avg_detail_ht = 0
        self._max_detail_ht = 0

    def newpage(self, canvas, row):
        if self.pagenumber:
            canvas.showPage()
        self.pagenumber += 1
        self.endofpage = self.pagesize[1] - self.bottommargin
        canvas.translate(0, self.pagesize[1])
        self.current_offset = self.topmargin
        if self.titleband and self.pagenumber == 1:
            elementlist = self.titleband.generate(row)
            self.current_offset += self.addtopage(canvas, elementlist)
        if self.pageheader:
            elementlist = self.pageheader.generate(row)
            self.current_offset += self.addtopage(canvas, elementlist)
        if self.reportheader and self.pagenumber == 1:
            elementlist = self.reportheader.generate(row)
            self.current_offset += self.addtopage(canvas, elementlist)
        if self.pagefooter:
            elementlist = self.pagefooter.generate(row)
            self.endofpage = self.pagesize[1] - self.bottommargin - elementlist[0]
            for el in elementlist[1:]:
                el.render(self.endofpage, canvas)

    def addtopage(self, canvas, elementlist):
        for el in elementlist[1:]:
            el.render(self.current_offset, canvas)
        return elementlist[0]

    def setreference(self, bands):
        for band in bands:
            if band is not None:
                for element in band.elements:
                    element.report = self
                self.setreference(band.childbands)
                self.setreference(band.additionalbands)
                for background in band.backgrounds:
                    background.report = self

    def generate(self, canvas):

        # every Element in every Band needs a reference to this Report
        self.setreference([
            self.titleband, self.detailband,
            self.pageheader, self.pagefooter,
            self.reportheader, self.reportfooter,
        ])
        self.setreference(self.groupheaders)
        self.setreference(self.groupfooters)

        self.pagesize = (int(canvas._pagesize[0]), int(canvas._pagesize[1]))
        self.current_offset = self.pagesize[1]
        self.pagenumber = 0
        self.endofpage = self.pagesize[1] - self.bottommargin
        prevrow = None
        firstrow = 1

        for row in self.datasource:

            if self.rowfunc is not None:
                row = self.rowfunc(row)

            if row is None:
                continue

            self.rownumber += 1

            if firstrow:
                firstrow = None
                for band in self.groupheaders:
                    elementlist = band.generate(row)
                    if (self.current_offset + elementlist[0]) >= self.endofpage:
                        self.newpage(canvas, row)
                    self.current_offset += self.addtopage(canvas, elementlist)
                    for aband in band.additionalbands:
                        elementlist = aband.generate(row)
                        if (self.current_offset + elementlist[0]) >= self.endofpage:
                            self.newpage(canvas, row)
                        self.current_offset += self.addtopage(canvas, elementlist)

            lastchanged = None
            for i in range(len(self.groupfooters)):
                if self.groupfooters[i].ischanged(row):
                    lastchanged = i
            if lastchanged is not None:
                for i in range(lastchanged+1):
                    elementlist = self.groupfooters[i].generate(prevrow)
                    if self.groupfooters[i].newpagebefore \
                    or (self.current_offset + elementlist[0]) >= self.endofpage:
                        self.newpage(canvas, prevrow)
                    self.current_offset += self.addtopage(canvas, elementlist)
                    for aband in self.groupfooters[i].additionalbands:
                        elementlist = aband.generate(row)
                        if (self.current_offset + elementlist[0]) >= self.endofpage:
                            self.newpage(canvas, row)
                        self.current_offset += self.addtopage(canvas, elementlist)
                    if self.groupfooters[i].newpageafter:
                        self.current_offset = self.pagesize[1]
            for band in self.groupfooters:
                band.summarize(row)

            firstchanged = None
            for i in range(len(self.groupheaders)):
                if self.groupheaders[i].ischanged(row):
                    if firstchanged is None:
                        firstchanged = i
            if firstchanged is not None:
                for i in range(firstchanged, len(self.groupheaders)):
                    elementlist = self.groupheaders[i].generate(row)
                    if self.groupheaders[i].newpagebefore \
                    or (self.current_offset + elementlist[0] + self._avg_detail_ht) >= self.endofpage:
                        self.newpage(canvas, row)
                    self.current_offset += self.addtopage(canvas, elementlist)
                    for aband in self.groupheaders[i].additionalbands:
                        elementlist = aband.generate(row)
                        if (self.current_offset + elementlist[0]) >= self.endofpage:
                            self.newpage(canvas, row)
                        self.current_offset += self.addtopage(canvas, elementlist)
                    if self.groupheaders[i].newpageafter:
                        self.current_offset = self.pagesize[1]

            if self.detailband is not None:
                elementlist = self.detailband.generate(row)
                self._max_detail_ht = max(elementlist[0], self._max_detail_ht)
                self._sum_detail_ht += elementlist[0]
                self._avg_detail_ht = \
                    ((self._sum_detail_ht // self.rownumber) + self._max_detail_ht) // 2
                if (self.current_offset + elementlist[0]) >= self.endofpage:
                    self.newpage(canvas, row)
                self.current_offset += self.addtopage(canvas, elementlist)
                for aband in self.detailband.additionalbands:
                    elementlist = aband.generate(row)
                    if (self.current_offset + elementlist[0]) >= self.endofpage:
                        self.newpage(canvas, row)
                    self.current_offset += self.addtopage(canvas, elementlist)

            if self.reportfooter:
                self.reportfooter.summarize(row)

            prevrow = row

        if prevrow:
            for band in self.groupfooters:
                elementlist = band.generate(prevrow)
                if band.newpagebefore or (self.current_offset + elementlist[0]) >= self.endofpage:
                    self.newpage(canvas, row)
                self.current_offset += self.addtopage(canvas, elementlist)
                for aband in band.additionalbands:
                    elementlist = aband.generate(row)
                    if (self.current_offset + elementlist[0]) >= self.endofpage:
                        self.newpage(canvas, row)
                    self.current_offset += self.addtopage(canvas, elementlist)
                if band.newpageafter:
                    self.current_offset = self.pagesize[1]

            if self.reportfooter:
                elementlist = self.reportfooter.generate(row)
                if self.reportfooter.newpagebefore or (self.current_offset + elementlist[0]) >= self.endofpage:
                    self.newpage(canvas, row)
                self.current_offset += self.addtopage(canvas, elementlist)
                for aband in self.reportfooter.additionalbands:
                    elementlist = aband.generate(row)
                    if (self.current_offset + elementlist[0]) >= self.endofpage:
                        self.newpage(canvas, row)
                    self.current_offset += self.addtopage(canvas, elementlist)

        canvas.showPage()


# end of file.
