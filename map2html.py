#!/usr/bin/env python3

from __future__ import with_statement
import getopt
import sys

from common import read_gcc, Symbol, Section


def main(fnSrc, fnDst):
    sections = read_gcc(fnSrc)
    sections = [x for x in sections if x.start > 0]

    with open(fnDst, 'w') as f:
        f.write('''
    <html>
    <head>
    <style>
        html { font-family: monospace; }
        body { display: flex; justify-content: center; }
        a { text-decoration: none; }
        .address { vertical-align: top; }
        .section { overflow: hidden; border: 2px solid black; -webkit-border-radius: 6px; border-radius: 6px; }
        .sectionName { font-weight: bold; display: inline-block; }
        .gap { background: lightgreen; border: 2px solid black; -webkit-border-radius: 6px; border-radius: 6px; }
        .files { table-layout: fixed; width: 100%; }
        .filename, .fileaddress, .filesize { background-color: lightblue; }
        .filename { width: 55%; }
        .fileaddress { width: 15%; }
        .filesize { width: 30%; }
    </style>
    </head>
    <body>
    <table cellspacing='1px'>''')
        last_end = 0xffffffff
        for sec in sorted(sections, key=lambda x:x.start):
            if last_end < sec.start:
                l = sec.start - last_end
                f.write('<tr><td class="address">%s</td><td class="gap">FREE %s (%s) bytes<td></tr>' % (hex(last_end), hex(l), l))
            f.write('<tr><td class="address">%s</td><td class="section"><div class="sectionName">%s</div> %s (%s) bytes<table class="files">' % (hex(sec.start), sec.name, hex(sec.length), sec.length))
            for file in sorted(sec.files, key=lambda x:x.start): # list of files within a section
                f.write('<tr><td class="filename">%s</td><td class="fileaddress">%s</td><td class="filesize">%s (%s) bytes</td></tr>' % (file.name, hex(file.start), hex(file.length), file.length))
                for symbol in sorted(file.symbols, key=lambda x:x.address):
                    f.write('<tr><td class="symbolname">%s</td><td class="symboladdress"> %s</td></tr>' % (symbol.name, hex(symbol.address)))
            f.write('</table></td></tr>')
            last_end = sec.start + sec.length
        f.write('''
        </table>
    </body>
    </html>
    ''')
    print("wrote %s file with %s sections" % (fnDst, len(sections)))



if __name__ == '__main__':
    src = ''
    dst = ''
    opts, args = getopt.getopt(sys.argv[1:], 'hi:o:', ['ifile=','ofile='])
    for opt, arg in opts:
        if opt == '-h':
           print("Usage:")
           print("map2html.py -i <inputfile> -o <outputfile>")
           print("  -i is required, -o can be inferred")
           sys.exit()
        elif opt == '-i':
            src = arg
            if len(dst) == 0:
                dst = src.rsplit('.', 1)[0] + '.html'
        elif opt == '-o':
            dst = arg
    if len(src) and len(dst):
        main(src, dst)
    else:
        print("valid input and output paths are required.  Use `-h` option for more details")
