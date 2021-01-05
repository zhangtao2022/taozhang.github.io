#!/usr/bin/env python

u"""jemdoc version 0.7.3, 2012-11-27."""

# Copyright (C) 2007-2012 Jacob Mattingley (jacobm@stanford.edu).
#
# This file is part of jemdoc.
#
# jemdoc is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# jemdoc is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
#
# The LaTeX equation portions of this file were initially based on
# latexmath2png, by Kamil Kisiel (kamil@kamikisiel.net).
#

from __future__ import absolute_import
import sys
import os
import re
import time
import StringIO
from subprocess import *
import tempfile
from io import open

def info():
  print __doc__
  print u'Platform: ' + sys.platform + u'.'
  print u'Python: %s, located at %s.' % (sys.version[:5], sys.executable)
  print u'Equation support:'
  (supported, message) = testeqsupport()
  if supported:
    print u'yes.'
  else:
    print u'no.'
  print message

def testeqsupport():
  supported = True
  msg = u''
  p = Popen(u'latex --version', shell=True, stdout=PIPE, stderr=PIPE)
  rc = p.wait()
  if rc != 0:
    msg += u'  latex: not found.\n'
    supported = False
  else:
    msg += u'  latex: ' + p.stdout.readlines()[0].rstrip() + u'.\n'
  p = Popen(u'dvipng --version', shell=True, stdout=PIPE, stderr=PIPE)
  rc = p.wait()
  if rc != 0:
    msg += u'  dvipng: not found.\n'
    supported = False
  else:
    msg += u'  dvipng: ' + p.stdout.readlines()[0].rstrip() + u'.\n'

  return (supported, msg[:-1])

class controlstruct(object):
  def __init__(self, infile, outfile=None, conf=None, inname=None, eqs=True,
         eqdir=u'eqs', eqdpi=130):
    self.inname = inname
    self.inf = infile
    self.outf = outfile
    self.conf = conf
    self.linenum = 0
    self.otherfiles = []
    self.eqs = eqs
    self.eqdir = eqdir
    self.eqdpi = eqdpi
    # Default to supporting equations until we know otherwise.
    self.eqsupport = True
    self.eqcache = True
    self.eqpackages = []
    self.texlines = []
    self.analytics = None
    self.eqbd = {} # equation base depth.
    self.baseline = None

  def pushfile(self, newfile):
    self.otherfiles.insert(0, self.inf)
    self.inf = open(newfile, u'rb')

  def nextfile(self):
    self.inf.close()
    self.inf = self.otherfiles.pop(0)

def showhelp():
  a = u"""Usage: jemdoc [OPTIONS] [SOURCEFILE] 
  Produces html markup from a jemdoc SOURCEFILE.

  Most of the time you can use jemdoc without any additional flags.
  For example, typing

    jemdoc index

  will produce an index.html from index.jemdoc, using a default
  configuration.

  Some configuration options can be overridden by specifying a
  configuration file.  You can use

    jemdoc --show-config

  to print a sample configuration file (which includes all of the
  default options). Any or all of the configuration [blocks] can be
  overwritten by including them in a configuration file, and running,
  for example,

    jemdoc -c mywebsite.conf index.jemdoc 

  You can view version and installation details with

    jemdoc --version

  See http://jemdoc.jaboc.net/ for many more details."""
  b = u''
  for l in a.splitlines(True):
    if l.startswith(u' '*4):
      b += l[4:]
    else:
      b += l

  print b

def standardconf():
  a = u"""[firstbit]
  <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
    "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
  <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
  <head>
  <meta name="generator" content="jemdoc, see http://jemdoc.jaboc.net/" />
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  
  [defaultcss]
  <link rel="stylesheet" href="jemdoc.css" type="text/css" />
  
  [windowtitle]
  # used in header for window title.
  <title>|</title>

  [fwtitlestart]
  <div id="fwtitle">

  [fwtitleend]
  </div>
  
  [doctitle]
  # used at top of document.
  <div id="toptitle">
  <h1>|</h1>
  
  [subtitle]
  <div id="subtitle">|</div>
  
  [doctitleend]
  </div>
  
  [bodystart]
  </head>
  <body>
  
  [analytics]
  <script type="text/javascript">
  var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
  document.write(unescape("%3Cscript src='" + gaJsHost + "google-analytics.com/ga.js' type='text/javascript'%3E%3C/script%3E"));
  </script>
  <script type="text/javascript">
  try {
      var pageTracker = _gat._getTracker("|");
      pageTracker._trackPageview();
  } catch(err) {}</script>
  
  [menustart]
  <table summary="Table for page layout." id="tlayout">
  <tr valign="top">
  <td id="layout-menu">
  
  [menuend]
  </td>
  <td id="layout-content">
  
  [menucategory]
  <div class="menu-category">|</div>

  [menuitem]
  <div class="menu-item"><a href="|1">|2</a></div>

  [specificcss]
  <link rel="stylesheet" href="|" type="text/css" />

  [specificjs]
  <script src="|.js" type="text/javascript"></script>
  
  [currentmenuitem]
  <div class="menu-item"><a href="|1" class="current">|2</a></div>
  
  [nomenu]
  <div id="layout-content">
  
  [menulastbit]
  </td>
  </tr>
  </table>
  
  [nomenulastbit]
  </div>
  
  [bodyend]
  </body>
  </html>
  
  [infoblock]
  <div class="infoblock">
  
  [codeblock]
  <div class="codeblock">
  
  [blocktitle]
  <div class="blocktitle">|</div>
  
  [infoblockcontent]
  <div class="blockcontent">
  
  [codeblockcontent]
  <div class="blockcontent"><pre>
  
  [codeblockend]
  </pre></div></div>
  
  [codeblockcontenttt]
  <div class="blockcontent"><tt class="tthl">
  
  [codeblockendtt]
  </tt></div></div>
  
  [infoblockend]
  </div></div>
  
  [footerstart]
  <div id="footer">
  <div id="footer-text">
  
  [footerend]
  </div>
  </div>
  
  [lastupdated]
  Page generated |, by <a href="http://jemdoc.jaboc.net/">jemdoc</a>.

  [sourcelink]
  (<a href="|">source</a>)

  """
  b = u''
  for l in a.splitlines(True):
    if l.startswith(u'  '):
      b += l[2:]
    else:
      b += l

  return b

class JandalError(Exception):
  pass

class NoEqSupport(Exception):
  pass

def raisejandal(msg, line=0):
  if line == 0:
    s = u"%s" % msg
  else:
    s = u"line %d: %s" % (line, msg)
  raise JandalError(s)

def readnoncomment(f):
  l = f.readline()
  if l == u'':
    return l
  elif l[0] == u'#': # jem: be a little more generous with the comments we accept?
    return readnoncomment(f)
  else:
    return l.rstrip() + u'\n' # leave just one \n and no spaces etc.

def parseconf(cns):
  syntax = {}
  warn = False # jem. make configurable?
  # manually add the defaults as a file handle.
  fs = [StringIO.StringIO(standardconf())]
  for sname in cns:
    fs.append(open(sname, u'rb'))

  for f in fs:
    while pc(controlstruct(f)) != u'':
      l = readnoncomment(f)
      r = re.match(ur'\[(.*)\]\n', l)

      if r:
        tag = r.group(1)

        s = u''
        l = readnoncomment(f)
        while l not in (u'\n', u''):
          s += l
          l = readnoncomment(f)

        syntax[tag] = s

    f.close()

  return syntax

def insertmenuitems(f, mname, current, prefix):
  m = open(mname, u'rb')
  while pc(controlstruct(m)) != u'':
    l = readnoncomment(m)
    l = l.strip()
    if l == u'':
      continue

    r = re.match(ur'\s*(.*?)\s*\[(.*)\]', l)

    if r: # then we have a menu item.
      link = r.group(2)
      # Don't use prefix if we have an absolute link.
      if u'://' not in r.group(2):
        link = prefix + allreplace(link)

      # replace spaces with nbsps.
      # do do this, even though css would make it work - ie ignores.
      # only replace spaces that aren't in {{ blocks.
      in_quote = False
      menuitem = u""
      for group in re.split(ur'({{|}})', r.group(1)):
        if in_quote:
          if group == u'}}':
            in_quote = False
            next
          else:
            menuitem += group
        else:
          if group == u'{{':
            in_quote = True
            next
          else:
            menuitem += br(re.sub(ur'(?<!\\n) +', u'~', group), f)

      if link[-len(current):] == current:
        hb(f.outf, f.conf[u'currentmenuitem'], link, menuitem)
      else:
        hb(f.outf, f.conf[u'menuitem'], link, menuitem)

    else: # menu category.
      hb(f.outf, f.conf[u'menucategory'], br(l, f))

  m.close()

def out(f, s):
  f.write(s)

def hb(f, tag, content1, content2=None):
  u"""Writes out a halfblock (hb)."""

  if content1 is None:
    content1 = u""

  if content2 is None:
    out(f, re.sub(ur'\|', content1, tag))
  else:
    r = re.sub(ur'\|1', content1, tag)
    r = re.sub(ur'\|2', content2, r)
    out(f, r)

def pc(f, ditchcomments=True):
  u"""Peeks at next character in the file."""
  # Should only be used to look at the first character of a new line.
  c = f.inf.read(1)
  if c: # only undo forward movement if we're not at the end.
    if ditchcomments and c == u'#':
      l = nl(f)
      if doincludes(f, l):
        return u"#"

    if c in u' \t':
      return pc(f)

    if c == u'\\':
      c += pc(f)

    f.inf.seek(-1, 1)
  elif f.otherfiles:
    f.nextfile()
    return pc(f, ditchcomments)

  return c

def doincludes(f, l):
  ir = u'includeraw{'
  i = u'include{'
  if l.startswith(ir):
    nf = open(l[len(ir):-2], u'rb')
    f.outf.write(nf.read())
    nf.close()
  elif l.startswith(i):
    f.pushfile(l[len(i):-2])
  else:
    return False

  return True

def nl(f, withcount=False, codemode=False):
  u"""Get input file line."""
  s = f.inf.readline()
  if not s and f.otherfiles:
    f.nextfile()
    return nl(f, withcount, codemode)

  f.linenum += 1

  if not codemode:
    # remove any special characters - assume they were checked by pc()
    # before we got here.
    # remove any trailing comments.
    s = s.lstrip(u' \t')
    s = re.sub(ur'\s*(?<!\\)#.*', u'', s)

  if withcount:
    if s[0] == u'.':
      m = ur'\.'
    else:
      m = s[0]

    r = re.match(u'(%s+) ' % m, s)
    if not r:
      raise SyntaxError(u"couldn't handle the jandal (code 12039) on line"
                u" %d" % f.linenum)

    if not codemode:
      s = s.lstrip(u'-.=:')

    return (s, len(r.group(1)))
  else:
    if not codemode:
      s = s.lstrip(u'-.=:')

    return s

def np(f, withcount=False, eatblanks=True):
  u"""Gets the next paragraph from the input file."""
  # New paragraph markers signalled by characters in following tuple.
  if withcount:
    (s, c) = nl(f, withcount)
  else:
    s = nl(f)

  while pc(f) not in (u'\n', u'-', u'.', u':', u'', u'=', u'~', u'{', u'\\(', u'\\)'):
    s += nl(f)

  while eatblanks and pc(f) == u'\n':
    nl(f) # burn blank line.

  # in both cases, ditch the trailing \n.
  if withcount:
    return (s[:-1], c)
  else:
    return s[:-1]

def quote(s):
  return re.sub(ur"""[\\*/+"'<>&$%\.~[\]-]""", ur'\\\g<0>', s)

def replacequoted(b):
  u"""Quotes {{raw html}} sections."""

  r = re.compile(ur'\{\{(.*?)\}\}', re.M + re.S)
  m = r.search(b)
  while m:
    qb = quote(m.group(1))

    b = b[:m.start()] + qb + b[m.end():]

    m = r.search(b, m.start())

  return b

def replacepercents(b):
  # replace %sections% as +{{sections}}+. Do not replace if within a link.

  r = re.compile(ur'(?<!\\)%(.*?)(?<!\\)%', re.M + re.S)
  m = r.search(b)
  while m:
    #qb = '+' + quote(m.group(1)) + '+'
    a = re.sub(ur'\[', ur'BSNOTLINKLEFT12039XX', m.group(1))
    a = re.sub(ur'\]', ur'BSNOTLINKRIGHT12039XX', a)
    qb = u'+{{' + a + u'}}+'

    b = b[:m.start()] + qb + b[m.end():]

    m = r.search(b, m.start())

  return b

def replaceequations(b, f):
  # replace $sections$ and \(sections\) as equations.
  rs = ((re.compile(ur'(?<!\\)\$(.*?)(?<!\\)\$', re.M + re.S), False),
     (re.compile(ur'(?<!\\)\\\((.*?)(?<!\\)\\\)', re.M + re.S), True))
  for (r, wl) in rs:
    m = r.search(b)
    while m:
      eq = m.group(1)
      if wl:
        fn = unicode(abs(hash(eq + u'wl120930alsdk')))
      else:
        fn = unicode(abs(hash(eq)))

      # Find out the baseline when we first encounter an equation (don't
      # bother, otherwise).
      # Other initialization stuff which we do only once we know we have
      # equations.
      if f.baseline is None:
        # See if the eqdir exists, and if not, create it.
        if not os.path.isdir(f.eqdir):
          os.mkdir(f.eqdir)

        # Check that the tools we need exist.
        (supported, message) = testeqsupport()
        if not supported:
          print u'WARNING: equation support disabled.'
          print message
          f.eqsupport = False
          return b

        # Calculate the baseline.
        eqt = u"0123456789xxxXXxX"
        (f.baseline, blfn) = geneq(f, eqt, dpi=f.eqdpi, wl=False,
                       outname=u'baseline-' + unicode(f.eqdpi))
        if os.path.exists(blfn):
          os.remove(blfn)

      fn = fn + u'-' + unicode(f.eqdpi)
      (depth, fullfn) = geneq(f, eq, dpi=f.eqdpi, wl=wl, outname=fn)
      fullfn = fullfn.replace(u'\\', u'/')

      offset = depth - f.baseline + 1

      eqtext = allreplace(eq)
      eqtext = eqtext.replace(u'\\', u'')
      eqtext = eqtext.replace(u'\n', u' ')

      # Double braces will cause problems with escaping of image tag.
      eqtext = eqtext.replace(u'{{', u'DOUBLEOPENBRACE')
      eqtext = eqtext.replace(u'}}', u'DOUBLECLOSEBRACE')

      if wl:
        b = b[:m.start()] + \
            u'{{\n<div class="eqwl"><img class="eqwl" src="%s" alt="%s" />\n<br /></div>}}' % (fullfn, eqtext) + b[m.end():]
      else:
        b = b[:m.start()] + \
          u'{{<img class="eq" src="%s" alt="%s" style="vertical-align: -%dpx" />}}' % (fullfn, eqtext, offset) + b[m.end():]

      # jem: also clean out line breaks in the alttext?
      m = r.search(b, m.start())

  return replacequoted(b)

def replaceimages(b):
  # works with [img{width}{height}{alttext} location caption].
  r = re.compile(ur'(?<!\\)\[img((?:\{.*?\}){,3})\s(.*?)(?:\s(.*?))?(?<!\\)\]',
           re.M + re.S)
  m = r.search(b)
  s = re.compile(ur'{(.*?)}', re.M + re.S)
  while m:
    m1 = list(s.findall(m.group(1)))
    m1 += [u'']*(3 - len(m1))

    bits = []
    link = m.group(2).strip()
    bits.append(ur'src=\"%s\"' % quote(link))

    if m1[0]:
      if m1[0].isdigit():
        s = m1[0] + u'px'
      else:
        s = m1[0]
      bits.append(ur'width=\"%s\"' % quote(s))
    if m1[1]:
      if m1[1].isdigit():
        s = m1[1] + u'px'
      else:
        s = m1[1]
      bits.append(ur'height=\"%s\"' % quote(s))
    if m1[2]:
      bits.append(ur'alt=\"%s\"' % quote(m1[2]))
    else:
      bits.append(ur'alt=\"\"')

    b = b[:m.start()] + ur'<img %s />' % u" ".join(bits) + b[m.end():]

    m = r.search(b, m.start())

  return b

def replacelinks(b):
  # works with [link.html new link style].
  r = re.compile(ur'(?<!\\)\[(.*?)(?:\s(.*?))?(?<!\\)\]', re.M + re.S)
  m = r.search(b)
  while m:
    m1 = m.group(1).strip()

    if u'@' in m1 and not m1.startswith(u'mailto:') and not \
       m1.startswith(u'http://'):
      link = u'mailto:' + m1
    else:
      link = m1

    # first unquote any hashes (e.g. for in-page links).
    link = re.sub(ur'\\#', u'#', link)

    # remove any +{{ or }}+ links.
    link = re.sub(ur'(\+\{\{|\}\}\+)', ur'%', link)

    link = quote(link)

    if m.group(2):
      linkname = m.group(2).strip()
    else:
      # remove any mailto before labelling.
      linkname = re.sub(u'^mailto:', u'', link)

    b = b[:m.start()] + ur'<a href=\"%s\">%s<\/a>' % (link, linkname) + b[m.end():]

    m = r.search(b, m.start())

  return b

def br(b, f, tableblock=False):
  u"""Does simple text replacements on a block of text. ('block replacements')"""

  # Deal with environment variables (say, for Michael Grant).
  r = re.compile(ur"!\$(\w{2,})\$!", re.M + re.S)

  for m in r.findall(b):
    repl = os.environ.get(m)
    if repl == None:
      b = re.sub(u"!\$%s\$!" % m, u'FAILED_MATCH_' + m, b)
    else:
      b = re.sub(u"!\$%s\$!" % m, repl, b)

  # Deal with literal backspaces.
  if f.eqs and f.eqsupport:
    b = replaceequations(b, f)

  b = re.sub(ur'\\\\', u'jemLITerl33talBS', b)

  # Deal with {{html embedding}}.
  b = replacequoted(b)

  b = allreplace(b)

  b = b.lstrip(u'-. \t') # remove leading spaces, tabs, dashes, dots.
  b = replaceimages(b) # jem not sure if this is still used.

  # Slightly nasty hackery in this next bit.
  b = replacepercents(b)
  b = replacelinks(b)
  b = re.sub(ur'BSNOTLINKLEFT12039XX', ur'[', b)
  b = re.sub(ur'BSNOTLINKRIGHT12039XX', ur']', b)
  b = replacequoted(b)

  # Deal with /italics/ first because the '/' in other tags would otherwise
  # interfere.
  r = re.compile(ur'(?<!\\)/(.*?)(?<!\\)/', re.M + re.S)
  b = re.sub(r, ur'<i>\1</i>', b)

  # Deal with *bold*.
  r = re.compile(ur'(?<!\\)\*(.*?)(?<!\\)\*', re.M + re.S)
  b = re.sub(r, ur'<b>\1</b>', b)

  # Deal with +monospace+.
  r = re.compile(ur'(?<!\\)\+(.*?)(?<!\\)\+', re.M + re.S)
  b = re.sub(r, ur'<tt>\1</tt>', b)

  # Deal with "double quotes".
  r = re.compile(ur'(?<!\\)"(.*?)(?<!\\)"', re.M + re.S)
  b = re.sub(r, ur'&ldquo;\1&rdquo;', b)

  # Deal with left quote `.
  r = re.compile(ur"(?<!\\)`", re.M + re.S)
  b = re.sub(r, ur'&lsquo;', b)

  # Deal with apostrophe '.
  # Add an assertion that the next character's not a letter, to deal with
  # apostrophes properly.
  r = re.compile(ur"(?<!\\)'(?![a-zA-Z])", re.M + re.S)
  b = re.sub(r, ur'&rsquo;', b)

  # Deal with em dash ---.
  r = re.compile(ur"(?<!\\)---", re.M + re.S)
  b = re.sub(r, ur'&#8201;&mdash;&#8201;', b)

  # Deal with en dash --.
  r = re.compile(ur"(?<!\\)--", re.M + re.S)
  b = re.sub(r, ur'&ndash;', b)

  # Deal with ellipsis ....
  r = re.compile(ur"(?<!\\)\.\.\.", re.M + re.S)
  b = re.sub(r, ur'&hellip;', b)

  # Deal with non-breaking space ~.
  r = re.compile(ur"(?<!\\)~", re.M + re.S)
  b = re.sub(r, ur'&nbsp;', b)

  # Deal with registered trademark \R.
  r = re.compile(ur"(?<!\\)\\R", re.M + re.S)
  b = re.sub(r, ur'&reg;', b)

  # Deal with copyright \C.
  r = re.compile(ur"(?<!\\)\\C", re.M + re.S)
  b = re.sub(r, ur'&copy;', b)

  # Deal with middot \M.
  r = re.compile(ur"(?<!\\)\\M", re.M + re.S)
  b = re.sub(r, ur'&middot;', b)

  # Deal with line break.
  r = re.compile(ur"(?<!\\)\\n", re.M + re.S)
  b = re.sub(r, ur'<br />', b)

  # Deal with paragraph break. Caution! Should only use when we're already in
  # a paragraph.
  r = re.compile(ur"(?<!\\)\\p", re.M + re.S)
  b = re.sub(r, ur'</p><p>', b)

  if tableblock:
    # Deal with ||, meaning </td></tr><tr><td>
    r = re.compile(ur"(?<!\\)\|\|", re.M + re.S)
    f.tablecol = 2
    bcopy = b
    b = u""
    r2 = re.compile(ur"(?<!\\)\|", re.M + re.S)
    for l in bcopy.splitlines():
      f.tablerow += 1
      l = re.sub(r, ur'</td></tr>\n<tr class="r%d"><td class="c1">' \
            % f.tablerow, l)

      l2 = u''
      col = 2
      r2s = r2.split(l)
      for x in r2s[:-1]:
        l2 += x + (u'</td><td class="c%d">' % col)
        col += 1
      l2 += r2s[-1]

      b += l2

  # Second to last, remove any remaining quoting backslashes.
  b = re.sub(ur'\\(?!\\)', u'', b)

  # Deal with literal backspaces.
  b = re.sub(u'jemLITerl33talBS', ur'\\', b)

  # Also fix up DOUBLEOPEN and DOUBLECLOSEBRACES.
  b = re.sub(u'DOUBLEOPENBRACE', u'{{', b)
  b = re.sub(u'DOUBLECLOSEBRACE', u'}}', b)

  return b

def allreplace(b):
  u"""Replacements that should be done on everything."""
  r = re.compile(ur"(?<!\\)&", re.M + re.S)
  b = re.sub(r, ur'&amp;', b)

  r = re.compile(ur"(?<!\\)>", re.M + re.S)
  b = re.sub(r, ur'&gt;', b)

  r = re.compile(ur"(?<!\\)<", re.M + re.S)
  b = re.sub(r, ur'&lt;', b)

  return b

def pyint(f, l):
  l = l.rstrip()
  l = allreplace(l)

  r = re.compile(ur'(#.*)')
  l = r.sub(ur'<span class = "comment">\1</span>', l)

  if l.startswith(u'&gt;&gt;&gt;'):
    hb(f, u'<span class="pycommand">|</span>\n', l)
  else:
    out(f, l + u'\n')

def putbsbs(l):
  for i in xrange(len(l)):
    l[i] = u'\\b' + l[i] + u'\\b'

  return l

def gethl(lang):
  # disable comments by default, by choosing unlikely regex.
  d = {u'strings':False}
  if lang in (u'py', u'python'):
    d[u'statement'] = [u'break', u'continue', u'del', u'except', u'exec',
              u'finally', u'pass', u'print', u'raise', u'return', u'try',
              u'with', u'global', u'assert', u'lambda', u'yield', u'def',
              u'class', u'for', u'while', u'if', u'elif', u'else',
              u'import', u'from', u'as', u'assert']
    d[u'builtin'] = [u'True', u'False', u'set', u'open', u'frozenset',
            u'enumerate', u'object', u'hasattr', u'getattr', u'filter',
            u'eval', u'zip', u'vars', u'unicode', u'type', u'str',
            u'repr', u'round', u'range', u'and', u'in', u'is', u'not',
            u'or']
    d[u'special'] = [u'cols', u'optvar', u'param', u'problem', u'norm2', u'norm1',
            u'value', u'minimize', u'maximize', u'rows', u'rand',
            u'randn', u'printval', u'matrix']
    d[u'error'] = [u'\w*Error',]
    d[u'commentuntilend'] = u'#'
    d[u'strings'] = True
  elif lang in [u'c', u'c++', u'cpp']:
    d[u'statement'] = [u'if', u'else', u'printf', u'return', u'for']
    d[u'builtin'] = [u'static', u'typedef', u'int', u'float', u'double', u'void',
            u'clock_t', u'struct', u'long', u'extern', u'char']
    d[u'operator'] = [u'#include.*', u'#define', u'@pyval{', u'}@', u'@pyif{',
             u'@py{']
    d[u'error'] = [u'\w*Error',]
    d[u'commentuntilend'] = [u'//', u'/*', u' * ', u'*/']
  elif lang in (u'rb', u'ruby'):
    d[u'statement'] = putbsbs([u'while', u'until', u'unless', u'if', u'elsif',
                  u'when', u'then', u'else', u'end', u'begin',
                  u'rescue', u'class', u'def'])
    d[u'operator'] = putbsbs([u'and', u'not', u'or'])
    d[u'builtin'] = putbsbs([u'true', u'false', u'require', u'warn'])
    d[u'special'] = putbsbs([u'IO'])
    d[u'error'] = putbsbs([u'\w*Error',])
    d[u'commentuntilend'] = u'#'
    d[u'strings'] = True
    d[u'strings'] = True
    if lang in [u'c++', u'cpp']:
      d[u'builtin'] += [u'bool', u'virtual']
      d[u'statement'] += [u'new', u'delete']
      d[u'operator'] += [u'&lt;&lt;', u'&gt;&gt;']
      d[u'special'] = [u'public', u'private', u'protected', u'template',
              u'ASSERT']
  elif lang == u'sh':
    d[u'statement'] = [u'cd', u'ls', u'sudo', u'cat', u'alias', u'for', u'do',
              u'done', u'in', ]
    d[u'operator'] = [u'&gt;', ur'\\', ur'\|', u';', u'2&gt;', u'monolith&gt;',
             u'kiwi&gt;', u'ant&gt;', u'kakapo&gt;', u'client&gt;']
    d[u'builtin'] = putbsbs([u'gem', u'gcc', u'python', u'curl', u'wget', u'ssh',
                u'latex', u'find', u'sed', u'gs', u'grep', u'tee',
                u'gzip', u'killall', u'echo', u'touch',
                u'ifconfig', u'git', u'(?<!\.)tar(?!\.)'])
    d[u'commentuntilend'] = u'#'
    d[u'strings'] = True
  elif lang == u'matlab':
    d[u'statement'] = putbsbs([u'max', u'min', u'find', u'rand', u'cumsum', u'randn', u'help',
                     u'error', u'if', u'end', u'for'])
    d[u'operator'] = [u'&gt;', u'ans =', u'>>', u'~', u'\.\.\.']
    d[u'builtin'] = putbsbs([u'csolve'])
    d[u'commentuntilend'] = u'%'
    d[u'strings'] = True
  elif lang == u'commented':
    d[u'commentuntilend'] = u'#'

  # Add bsbs (whatever those are).
  for x in [u'statement', u'builtin', u'special', u'error']:
    if x in d:
      d[x] = putbsbs(d[x])

  return d

def language(f, l, hl):
  l = l.rstrip()
  l = allreplace(l)
  # handle strings.
  if hl[u'strings']:
    r = re.compile(ur'(".*?")')
    l = r.sub(ur'<span CLCLclass="string">\1</span>', l)
    r = re.compile(ur"('.*?')")
    l = r.sub(ur'<span CLCLclass="string">\1</span>', l)

  if u'statement' in hl:
    r = re.compile(u'(' + u'|'.join(hl[u'statement']) + u')')
    l = r.sub(ur'<span class="statement">\1</span>', l)

  if u'operator' in hl:
    r = re.compile(u'(' + u'|'.join(hl[u'operator']) + u')')
    l = r.sub(ur'<span class="operator">\1</span>', l)

  if u'builtin' in hl:
    r = re.compile(u'(' + u'|'.join(hl[u'builtin']) + u')')
    l = r.sub(ur'<span class="builtin">\1</span>', l)

  if u'special' in hl:
    r = re.compile(u'(' + u'|'.join(hl[u'special']) + u')')
    l = r.sub(ur'<span class="special">\1</span>', l)

  if u'error' in hl:
    r = re.compile(u'(' + u'|'.join(hl[u'error']) + u')')
    l = r.sub(ur'<span class="error">\1</span>', l)

  l = re.sub(u'CLCLclass', u'class', l)

  if u'commentuntilend' in hl:
    cue = hl[u'commentuntilend']
    if isinstance(cue, (list, tuple)):
      for x in cue:
        if l.strip().startswith(x):
          hb(f, u'<span class="comment">|</span>\n', allreplace(l))
          return
        if u'//' in cue: # Handle this separately.
          r = re.compile(ur'\/\/.*')
          l = r.sub(ur'<span class="comment">\g<0></span>', l)
    elif cue == u'#': # Handle this separately.
      r = re.compile(ur'#.*')
      l = r.sub(ur'<span class="comment">\g<0></span>', l)
    elif cue == u'%': # Handle this separately.
      r = re.compile(ur'%.*')
      l = r.sub(ur'<span class="comment">\g<0></span>', l)
    elif l.strip().startswith(cue):
      hb(f, u'<span class="comment">|</span>\n', allreplace(l))
      return

  out(f, l + u'\n')

def geneq(f, eq, dpi, wl, outname):
  # First check if there is an existing file.
  eqname = os.path.join(f.eqdir, outname + u'.png')

  eqdepths = {}
  if f.eqcache:
    try:
      dc = open(os.path.join(f.eqdir, u'.eqdepthcache'), u'rb')
      for l in dc:
        a = l.split()
        eqdepths[a[0]] = int(a[1])
      dc.close()

      if os.path.exists(eqname) and eqname in eqdepths:
        return (eqdepths[eqname], eqname)
    except IOError:
      print u'eqdepthcache read failed.'

  # Open tex file.
  tempdir = tempfile.gettempdir()
  fd, texfile = tempfile.mkstemp(u'.tex', u'', tempdir, True)
  basefile = texfile[:-4]
  g = os.fdopen(fd, u'wb')

  preamble = u'\\documentclass{article}\\n'
  for p in f.eqpackages:
    preamble += u'\\usepackage{%s}\\n' % p
  for p in f.texlines:
    # Replace \{ and \} in p with { and }.
    # XXX hack.
    preamble += re.sub(ur'\\(?=[{}])', u'', p + u'\n')
  preamble += u'\pagestyle{empty}\n\\begin{document}\n'
  g.write(preamble)
  
  # Write the equation itself.
  if wl:
    g.write(u'\\[%s\\]' % eq)
  else:
    g.write(u'$%s$' % eq)

  # Finish off the tex file.
  g.write(u'\n\\newpage\n\end{document}')
  g.close()

  exts = [u'.tex', u'.aux', u'.dvi', u'.log']
  try:
    # Generate the DVI file
    latexcmd = u'latex -file-line-error-style -interaction=nonstopmode ' + \
         u'-output-directory %s %s' % (tempdir, texfile)
    p = Popen(latexcmd, shell=True, stdout=PIPE)
    rc = p.wait()
    if rc != 0:
      for l in p.stdout.readlines():
        print u'  ' + l.rstrip()
      exts.remove(u'.tex')
      raise Exception(u'latex error')

    dvifile = basefile + u'.dvi'
    dvicmd = u'dvipng --freetype0 -Q 9 -z 3 --depth -q -T tight -D %i -bg Transparent -o %s %s' % (dpi, eqname, dvifile)
    # discard warnings, as well.
    p = Popen(dvicmd, shell=True, stdout=PIPE, stderr=PIPE)
    rc = p.wait()
    if rc != 0:
      print p.stderr.readlines()
      raise Exception(u'dvipng error')
    depth = int(p.stdout.readlines()[-1].split(u'=')[-1])
  finally:
    # Clean up.
    for ext in exts:
      g = basefile + ext
      if os.path.exists(g):
        os.remove(g)

  # Update the cache if we're using it.
  if f.eqcache and eqname not in eqdepths:
    try:
      dc = open(os.path.join(f.eqdir, u'.eqdepthcache'), u'ab')
      dc.write(eqname + u' ' + unicode(depth) + u'\n')
      dc.close()
    except IOError:
      print u'eqdepthcache update failed.'
  return (depth, eqname)

def dashlist(f, ordered=False):
  level = 0

  if ordered:
    char = u'.'
    ul = u'ol'
  else:
    char = u'-'
    ul = u'ul'

  while pc(f) == char:
    (s, newlevel) = np(f, True, False)

    # first adjust list number as appropriate.
    if newlevel > level:
      for i in xrange(newlevel - level):
        if newlevel > 1:
          out(f.outf, u'\n')
        out(f.outf, u'<%s>\n<li>' % ul)
    elif newlevel < level:
      out(f.outf, u'\n</li>')
      for i in xrange(level - newlevel):
        #out(f.outf, '</li>\n</%s>\n</li><li>' % ul)
        # demote means place '</ul></li>' in the file.
        out(f.outf, u'</%s>\n</li>' % ul)
      #out(f.outf, '\n<li>')
      out(f.outf, u'\n<li>')
    else:
      # same level, make a new list item.
      out(f.outf, u'\n</li>\n<li>')

    out(f.outf, u'<p>' + br(s, f) + u'</p>')
    level = newlevel

  for i in xrange(level):
    out(f.outf, u'\n</li>\n</%s>\n' % ul)

def colonlist(f):
  out(f.outf, u'<dl>\n')
  while pc(f) == u':':
    s = np(f, eatblanks=False)
    r = re.compile(ur'\s*{(.*?)(?<!\\)}(.*)', re.M + re.S)
    g = re.match(r, s)

    if not g or len(g.groups()) != 2:
      raise SyntaxError(u"couldn't handle the jandal (invalid deflist "
               u"format) on line %d" % f.linenum)
    # split into definition / non-definition part.
    defpart = g.group(1)
    rest = g.group(2)

    hb(f.outf, u'<dt>|</dt>\n', br(defpart, f))
    hb(f.outf, u'<dd><p>|</p></dd>\n', br(rest, f))

  out(f.outf, u'</dl>\n')

def codeblock(f, g):
  if g[1] == u'raw':
    raw = True
    ext_prog = None
  elif g[0] == u'filter_through':
    # Filter through external program.
    raw = False
    ext_prog = g[1]
    buff = u""
  else:
    ext_prog = None
    raw = False
    out(f.outf, f.conf[u'codeblock'])
    if g[0]:
      hb(f.outf, f.conf[u'blocktitle'], g[0])
    if g[1] == u'jemdoc':
      out(f.outf, f.conf[u'codeblockcontenttt'])
    else:
      out(f.outf, f.conf[u'codeblockcontent'])

  # Now we are handling code.
  # Handle \~ and ~ differently.
  stringmode = False
  while 1: # wait for EOF.
    l = nl(f, codemode=True)
    if not l:
      break
    elif l.startswith(u'~'):
      break
    elif l.startswith(u'\\~'):
      l = l[1:]
    elif l.startswith(u'\\{'):
      l = l[1:]
    elif ext_prog:
      buff += l
      continue
    elif stringmode:
      if l.rstrip().endswith(u'"""'):
        out(f.outf, l + u'</span>')
        stringmode = False
      else:
        out(f.outf, l)
      continue

    # jem revise pyint out of the picture.
    if g[1] == u'pyint':
      pyint(f.outf, l)
    else:
      if raw:
        out(f.outf, l)
      elif g[1] == u'jemdoc':
        # doing this more nicely needs python 2.5.
        for x in (u'#', u'~', u'>>>', u'\~', u'{'):
          if unicode(l).lstrip().startswith(x):
            out(f.outf, u'</tt><pre class="tthl">')
            out(f.outf, l + u'</pre><tt class="tthl">')
            break
        else:
          for x in (u':', u'.', u'-'):
            if unicode(l).lstrip().startswith(x):
              out(f.outf, u'<br />' + prependnbsps(l))
              break
          else:
            if unicode(l).lstrip().startswith(u'='):
              out(f.outf, prependnbsps(l) + u'<br />')
            else:
              out(f.outf, l)
      else:
        if l.startswith(u'\\#include{') or l.startswith(u'\\#includeraw{'):
          out(f.outf, l[1:])
        elif l.startswith(u'#') and doincludes(f, l[1:]):
          continue
        elif g[1] in (u'python', u'py') and l.strip().startswith(u'"""'):
          out(f.outf, u'<span class="string">' + l)
          stringmode = True
        else:
          language(f.outf, l, gethl(g[1]))

  if raw:
    return
  elif ext_prog:
    print u'filtering through %s...' % ext_prog

    output,_ = Popen(ext_prog, shell=True, stdin=PIPE,
                     stdout=PIPE).communicate(buff)
    out(f.outf, output)
  else:
    if g[1] == u'jemdoc':
      out(f.outf, f.conf[u'codeblockendtt'])
    else:
      out(f.outf, f.conf[u'codeblockend'])

def prependnbsps(l):
  g = re.search(u'(^ *)(.*)', l).groups()
  return g[0].replace(u' ', u'&nbsp;') + g[1]

def inserttitle(f, t):
  if t is not None:
    hb(f.outf, f.conf[u'doctitle'], t)

    # Look for a subtitle.
    if pc(f) != u'\n':
      hb(f.outf, f.conf[u'subtitle'], br(np(f), f))

    hb(f.outf, f.conf[u'doctitleend'], t)

def procfile(f):
  f.linenum = 0

  menu = None
  # convert these to a dictionary.
  showfooter = True
  showsourcelink = False
  showlastupdated = True
  showlastupdatedtime = True
  nodefaultcss = False
  fwtitle = False
  css = []
  js = []
  title = None
  while pc(f, False) == u'#':
    l = f.inf.readline()
    f.linenum += 1
    if doincludes(f, l[1:]):
      continue
    if l.startswith(u'# jemdoc:'):
      l = l[len(u'# jemdoc:'):]
      a = l.split(u',')
      # jem only handle one argument for now.
      for b in a:
        b = b.strip()
        if b.startswith(u'menu'):
          sidemenu = True
          r = re.compile(ur'(?<!\\){(.*?)(?<!\\)}', re.M + re.S)
          g = re.findall(r, b)
          if len(g) > 3 or len(g) < 2:
            raise SyntaxError(u'sidemenu error on line %d' % f.linenum)

          if len(g) == 2:
            menu = (f, g[0], g[1], u'')
          else:
            menu = (f, g[0], g[1], g[2])

        elif b.startswith(u'nofooter'):
          showfooter = False

        elif b.startswith(u'nodate'):
          showlastupdated = False

        elif b.startswith(u'notime'):
          showlastupdatedtime = False

        elif b.startswith(u'fwtitle'):
          fwtitle = True

        elif b.startswith(u'showsource'):
          showsourcelink = True

        elif b.startswith(u'nodefaultcss'):
          nodefaultcss = True

        elif b.startswith(u'addcss'):
          r = re.compile(ur'(?<!\\){(.*?)(?<!\\)}', re.M + re.S)
          css += re.findall(r, b)

        elif b.startswith(u'addjs'):
          r = re.compile(ur'(?<!\\){(.*?)(?<!\\)}', re.M + re.S)
          js += re.findall(r, b)

        elif b.startswith(u'addpackage'):
          r = re.compile(ur'(?<!\\){(.*?)(?<!\\)}', re.M + re.S)
          f.eqpackages += re.findall(r, b)

        elif b.startswith(u'addtex'):
          r = re.compile(ur'(?<!\\){(.*?)(?<!\\)}', re.M + re.S)
          f.texlines += re.findall(r, b)

        elif b.startswith(u'analytics'):
          r = re.compile(ur'(?<!\\){(.*?)(?<!\\)}', re.M + re.S)
          f.analytics = re.findall(r, b)[0]

        elif b.startswith(u'title'):
          r = re.compile(ur'(?<!\\){(.*?)(?<!\\)}', re.M + re.S)
          g = re.findall(r, b)
          if len(g) != 1:
            raise SyntaxError(u'addtitle error on line %d' % f.linenum)

          title = g[0]

        elif b.startswith(u'noeqs'):
          f.eqs = False

        elif b.startswith(u'noeqcache'):
          f.eqcache = False

        elif b.startswith(u'eqsize'):
          r = re.compile(ur'(?<!\\){(.*?)(?<!\\)}', re.M + re.S)
          g = re.findall(r, b)
          if len(g) != 1:
            raise SyntaxError(u'eqsize error on line %d' % f.linenum)

          f.eqdpi = int(g[0])

        elif b.startswith(u'eqdir'):
          r = re.compile(ur'(?<!\\){(.*?)(?<!\\)}', re.M + re.S)
          g = re.findall(r, b)
          if len(g) != 1:
            raise SyntaxError(u'eqdir error on line %d' % f.linenum)

          f.eqdir = g[0]

  # Get the file started with the firstbit.
  out(f.outf, f.conf[u'firstbit'])

  if not nodefaultcss:
    out(f.outf, f.conf[u'defaultcss'])

  # Add per-file css lines here.
  for i in xrange(len(css)):
    if u'.css' not in css[i]:
      css[i] += u'.css'

  for x in css:
    hb(f.outf, f.conf[u'specificcss'], x)

  for x in js:
    hb(f.outf, f.conf[u'specificjs'], x)

  # Look for a title.
  if pc(f) == u'=': # don't check exact number f.outf '=' here jem.
    t = br(nl(f), f)[:-1]
    if title is None:
      title = re.sub(u' *(<br />)|(&nbsp;) *', u' ', t)
  else:
    t = None

  #if title:
  hb(f.outf, f.conf[u'windowtitle'], title)

  out(f.outf, f.conf[u'bodystart'])


  if f.analytics:
    hb(f.outf, f.conf[u'analytics'], f.analytics)

  if fwtitle:
    out(f.outf, f.conf[u'fwtitlestart'])
    inserttitle(f, t)
    out(f.outf, f.conf[u'fwtitleend'])

  if menu:
    out(f.outf, f.conf[u'menustart'])
    insertmenuitems(*menu)
    out(f.outf, f.conf[u'menuend'])
  else:
    out(f.outf, f.conf[u'nomenu'])

  if not fwtitle:
    inserttitle(f, t)

  infoblock = False
  imgblock = False
  tableblock = False
  while 1: # wait for EOF.
    p = pc(f)

    if p == u'':
      break

    elif p == u'\\(':
      if not (f.eqs and f.eqsupport):
        break

      s = nl(f)
      # Quickly pull out the equation here:
      # Check we don't already have the terminating character in a whole-line
      # equation without linebreaks, eg \( Ax=b \):
      if not s.strip().endswith(u'\)'):
        while True:
          l = nl(f, codemode=True)
          if not l:
            break
          s += l
          if l.strip() == u'\)':
            break
      out(f.outf, br(s.strip(), f))

    # look for lists.
    elif p == u'-':
      dashlist(f, False)

    elif p == u'.':
      dashlist(f, True)

    elif p == u':':
      colonlist(f)

    # look for titles.
    elif p == u'=':
      (s, c) = nl(f, True)
      # trim trailing \n.
      s = s[:-1]
      hb(f.outf, u'<h%d>|</h%d>\n' % (c, c), br(s, f))

    # look for comments.
    elif p == u'#':
      l = nl(f)

    elif p == u'\n':
      nl(f)

    # look for blocks.
    elif p == u'~':
      nl(f)
      if infoblock:
        out(f.outf, f.conf[u'infoblockend'])
        infoblock = False
        nl(f)
        continue
      elif imgblock:
        out(f.outf, u'</td></tr></table>\n')
        imgblock = False
        nl(f)
        continue
      elif tableblock:
        out(f.outf, u'</td></tr></table>\n')
        tableblock = False
        nl(f)
        continue
      else:
        if pc(f) == u'{':
          l = allreplace(nl(f))
          r = re.compile(ur'(?<!\\){(.*?)(?<!\\)}', re.M + re.S)
          g = re.findall(r, l)
        else:
          g = []

        # process jemdoc markup in titles.
        if len(g) >= 1:
          g[0] = br(g[0], f)

        if len(g) in (0, 1): # info block.
          out(f.outf, f.conf[u'infoblock'])
          infoblock = True
          
          if len(g) == 1: # info block.
            hb(f.outf, f.conf[u'blocktitle'], g[0])

          out(f.outf, f.conf[u'infoblockcontent'])

        elif len(g) >= 2 and g[1] == u'table':
          # handles
          # {title}{table}{name}
          # one | two ||
          # three | four ||
          name = u''
          if len(g) >= 3 and g[2]:
            name += u' id="%s"' % g[2]
          out(f.outf, u'<table%s>\n<tr class="r1"><td class="c1">' % name)
          f.tablerow = 1
          f.tablecol = 1

          tableblock = True

        elif len(g) == 2:
          codeblock(f, g)

        elif len(g) >= 4 and g[1] == u'img_left':
          # handles
          # {}{img_left}{source}{alttext}{width}{height}{linktarget}.
          g += [u'']*(7 - len(g))
          
          if g[4].isdigit():
            g[4] += u'px'

          if g[5].isdigit():
            g[5] += u'px'

          out(f.outf, u'<table class="imgtable"><tr><td>\n')
          if g[6]:
            out(f.outf, u'<a href="%s">' % g[6])
          out(f.outf, u'<img src="%s"' % g[2])
          out(f.outf, u' alt="%s"' % g[3])
          if g[4]:
            out(f.outf, u' width="%s"' % g[4])
          if g[5]:
            out(f.outf, u' height="%s"' % g[5])
          out(f.outf, u' />')
          if g[6]:
            out(f.outf, u'</a>')
          out(f.outf, u'&nbsp;</td>\n<td align="left">')
          imgblock = True

        else:
          raise JandalError(u"couldn't handle block", f.linenum)

    else:
      s = br(np(f), f, tableblock)
      if s:
        if tableblock:
          hb(f.outf, u'|\n', s)
        else:
          hb(f.outf, u'<p>|</p>\n', s)

  if showfooter and (showlastupdated or showsourcelink):
    out(f.outf, f.conf[u'footerstart'])
    if showlastupdated:
      if showlastupdatedtime:
        ts = u'%Y-%m-%d %H:%M:%S %Z'
      else:
        ts = u'%Y-%m-%d'
      s = time.strftime(ts, time.localtime(time.time()))
      hb(f.outf, f.conf[u'lastupdated'], s)
    if showsourcelink:
      hb(f.outf, f.conf[u'sourcelink'], f.inname)
    out(f.outf, f.conf[u'footerend'])

  if menu:
    out(f.outf, f.conf[u'menulastbit'])
  else:
    out(f.outf, f.conf[u'nomenulastbit'])

  out(f.outf, f.conf[u'bodyend'])

  if f.outf is not sys.stdout:
    # jem: close file here.
    # jem: XXX this is where you would intervene to do a fast open/close.
    f.outf.close()

def main():
  if len(sys.argv) == 1 or sys.argv[1] in (u'--help', u'-h'):
    showhelp()
    raise SystemExit
  if sys.argv[1] == u'--show-config':
    print standardconf()
    raise SystemExit
  if sys.argv[1] == u'--version':
    info()
    raise SystemExit

  outoverride = False
  confoverride = False
  outname = None
  confnames = []
  for i in xrange(1, len(sys.argv), 2):
    if sys.argv[i] == u'-o':
      if outoverride:
        raise RuntimeError(u"only one output file / directory, please")
      outname = sys.argv[i+1]
      outoverride = True
    elif sys.argv[i] == u'-c':
      if confoverride:
        raise RuntimeError(u"only one config file, please")
      confnames.append(sys.argv[i+1])
      confoverride = True
    elif sys.argv[i].startswith(u'-'):
      raise RuntimeError(u'unrecognised argument %s, try --help' % sys.argv[i])
    else:
      break

  conf = parseconf(confnames)

  innames = []
  for j in xrange(i, len(sys.argv)):
    # First, if not a file and no dot, try opening .jemdoc. Otherwise, fall back
    # to just doing exactly as asked.
    inname = sys.argv[j]
    if not os.path.isfile(inname) and u'.' not in inname:
      inname += u'.jemdoc'

    innames.append(inname)

  if outname is not None and not os.path.isdir(outname) and len(innames) > 1:
    raise RuntimeError(u'cannot handle one outfile with multiple infiles')

  for inname in innames:
    if outname is None:
      thisout = re.sub(ur'.jemdoc$', u'', inname) + u'.html'
    elif os.path.isdir(outname):
      # if directory, prepend directory to automatically generated name.
      thisout = outname + re.sub(ur'.jemdoc$', u'', inname) + u'.html'
    else:
      thisout = outname

    infile = open(inname, u'rUb')
    outfile = open(thisout, u'w')

    f = controlstruct(infile, outfile, conf, inname)
    procfile(f)

#
if __name__ == u'__main__':
  main()

