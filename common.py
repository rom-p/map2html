from enum import Enum, auto
from dataclasses import dataclass, field
import os.path
import re
import string


# gcc's .map files contain several parts (chapters)
# each "chapter" is deliniated by \n\n<name>\n\n
                            # the names of the chapters (case preserved)
class Chapter(Enum):
    DISCARDED = 0,          # "Discarded input sections"
    CONFIGURATION = auto(), # "Memory Configuration"
    SCRIPT = auto(),        # "Linker script and memory map"
    X_REFERENCE = auto(),   # "Cross Reference Table"
    UNKNOWN = auto()


def is_hexnum(s):
    if s.startswith('0x'):
        s = s[2:]
    hex_digits = set(string.hexdigits)
    return all(c in hex_digits for c in s)


@dataclass
class Symbol:
    name: str = ""
    address: int = -1
    size: int = -1
    type: int = 0


@dataclass
class FileSection:
    ''' each section might have multiple files'''
    name: str = ""
    start: int = -1
    length: int = -1
    symbols: list[Symbol] = field(default_factory=list[Symbol])


@dataclass
class Section:
    name: str = ""
    start: int = -1
    length: int = -1
    files: list[FileSection] = field(default_factory=list[FileSection])


def get_short_section_name(s: str) -> str:
    s = s.replace('*fill*', '')
    s = s.replace('SORT_BY_NAME', '')
    if len(s) == 0:
        return ''
    s = re.sub(r'[^0-9A-Za-z_\.]', '', s)
    section_names = list(filter(lambda x: len(x) > 0, re.split(r'\.', s)))
    return section_names[0]


def add_file(current_section, current_file_name, start, length, *, remove_path = True):
    if remove_path:
        current_file_name = os.path.basename(current_file_name)
    if current_section:
        current_file = FileSection(current_file_name, start, length)
        current_section.files.append(current_file)
        old_end = current_section.start + current_section.length
        if current_section.start == -1:
            current_section.start = start
        else:
            current_section.start = min(current_section.start, start)
        current_section.length = max(old_end, start + length) - current_section.start
        return current_file
    return None


'''   Here's an example of a typical .map file

// this is start and size of a section.  This creates a new `section`
.text           0x0000000007fc0110     0x4196

// this is part of a rule from the .ld file.  This is essentially ignored
 *(.isr_impl)

// this is matching sub-section with file name.  This goes into `section[].files`
 .isr_impl      0x0000000007fc0110        0x2 .obj/__sdk__/platform/arch/boot/GCC/ivtable_DA14531.S.o

// this is individual symbol name.  This goes into `section[].files[].symbols`
                0x0000000007fc0110                RESERVED23_Handler
'''


'''   This function returns:
  * the list of sections found in the file, e.g. `.text`, `.data`, or `.bss`, among many others
  * each sections contains the list of files that contribute symbols to the section
  * each file contains the list of symbols in this file, in this section
'''
def read_gcc(src : str, *, merge_sibling_subsections = True, remove_path = True):
    sections = []
    current_file = None
    current_section = None
    next_line_is_new_section_name = True
    chapter = Chapter.UNKNOWN
    with open(src, encoding = "Latin-1") as f:
        line = 0
        for ln in list(f):
            line += 1
            if next_line_is_new_section_name:
                if ln.strip() == "Linker script and memory map":
                    chapter = Chapter.SCRIPT            #  the addresses and sizes are here
                elif ln.strip() == "Cross Reference Table":
                    chapter = Chapter.X_REFERENCE
                next_line_is_new_section_name = False

            parts = re.split(r'\s+', ln.strip())

            if len(parts) == 1 and len(parts[0]) == 0:
                next_line_is_new_section_name = True
                continue

            if chapter == Chapter.SCRIPT:
                if not ln.startswith(" "):        # this is section start
                    section_name = parts[0]
                    start = -1
                    length = -1
                    if len(parts) == 1:
                        current_section = Section(section_name)
                    elif len(parts) == 3 and is_hexnum(parts[1]) and is_hexnum(parts[2]):
                        start = int(parts[1], 16)
                        length = int(parts[2], 16)
                    current_section = next((x for x in sections if x.name == section_name), None)
                    if current_section is None:
                        current_section = Section(section_name, start, length)
                        sections.append(current_section)
                    else:
                        old_end = current_section.start + current_section.length
                        current_section.start = min(current_section.start, start)
                        current_section.length = max(old_end, start + length) - current_section.start
                elif len(parts) == 1:
                    subsection_name = parts[0]
                    if merge_sibling_subsections:
                        subsection_name = get_short_section_name(subsection_name)
                elif len(parts) == 2:  # treat this as a symbol
                    if current_file and is_hexnum(parts[0]) and not is_hexnum(parts[1]):
                        addr = int(parts[0], 16)
                        symbol_name = parts[1]
                        current_file.symbols.append(Symbol(symbol_name, addr))
                elif len(parts) == 3:       # this looks like a file or section name
                    if not is_hexnum(parts[0]) and is_hexnum(parts[1]) and is_hexnum(parts[2]):   # section-name, addr, size
                        subsection_name = parts[0]
                        if merge_sibling_subsections:
                            subsection_name = get_short_section_name(subsection_name)
                    elif is_hexnum(parts[0]) and is_hexnum(parts[1]) and not is_hexnum(parts[2]): # addr, size, file-name
                        start = int(parts[0], 16)
                        length = int(parts[1], 16)
                        file_name = parts[2]
                        current_file = add_file(current_section, file_name, start, length, remove_path = remove_path)
                elif len(parts) == 4:       # subsection-name, addr, size, filename
                    if current_section and not is_hexnum(parts[0]) and is_hexnum(parts[1]) and is_hexnum(parts[2]):
                        subsection_name = parts[0]
                        start = int(parts[1], 16)
                        length = int(parts[2], 16)
                        file_name = parts[3]
                        current_file = add_file(current_section, file_name + "::" + subsection_name, start, length, remove_path = remove_path)
    return sections


if __name__ == "__main__":
    print("this is a library used by tools in this directory.  Please run the tools instead")
