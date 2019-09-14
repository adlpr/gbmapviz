#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys, os, re, argparse
from jinja2 import Environment, FileSystemLoader

def main(args):
    # normalize input filename
    inf_name = args.inf_name
    if not inf_name.endswith('.map'):
        inf_name += '.map'

    with open(inf_name,'r') as inf:
        rgbasm_map = RGBASMMap(inf, args.w)

    with open(inf_name+".html",'w') as outf:
        outf.write(rgbasm_map.to_html())


class RGBASMMap:
    """
    Parse a .map file generated by rgbds linker (`rgblink`) into a list of RGBASMMapBank objs
    """
    def __init__(self, inf, wram_single_bank, template_name="template.html"):
        self.wram_single_bank = wram_single_bank
        self.banks = self.__parse(inf.read())
        self.html_template = Environment(loader=FileSystemLoader(searchpath=os.path.dirname(__file__))).get_template(template_name)

    def to_html(self):
        return self.html_template.render(gbmap=self)

    def __parse(self, map_str):
        # split by bank and parse
        bank_strs = map_str.replace('\r','\n').strip().split('\n\n')
        banks = [RGBASMMapBank(bank_str, self.wram_single_bank) for bank_str in bank_strs]
        return banks


class RGBASMMapBank:
    """
    Parse a single bank string into its name and a sorted list of RGBASMMapSection objs
    """
    def __init__(self, bank_str, wram_single_bank):
        self.wram_single_bank = wram_single_bank
        self.name, self.sections = self.__parse(bank_str)
        self.size = self.__get_size()
        self.start_address = self.__get_start_address()
        self.color_palette = self.__get_color_palette()

    def __len__(self):
        return sum(map(len, self.sections))

    def to_svg(self, width=800, height=60):
        result = ""
        # add <rect> elements for each section
        current_color_i = -1
        for section in self.sections:
            # modulate x/width to total width
            x = (section.start - self.start_address) * width / self.size
            section_width = len(section) * width / self.size
            # if width > 0, move to next color in palette (cycle through)
            if section_width > 0:
                current_color_i = (current_color_i + 1) % len(self.color_palette)
            section_title = f'${section.start:04X}{f"&ndash;${section.end:04X}" if len(section) > 0 else ""}: {section.name}'
            result += f'<rect x="{x}" y="0" width="{section_width}" height="{height}" style="fill:rgb{self.color_palette[current_color_i]}"><title>{section_title}</title></rect>'
        return f'<svg width="{width}" height="{height}">{result}</svg>'

    def to_html_table(self):
        result = ""
        # concatenate rows from each section
        current_bg_color_i = -1
        for i, section in enumerate(self.sections):
            # if length > 0, move to next color in palette (cycle through)
            if len(section) > 0:
                current_bg_color_i = (current_bg_color_i + 1) % len(self.color_palette)
                current_bg_color = self.color_palette[current_bg_color_i]
            else:
                current_bg_color = (255,255,255)
            result += section.to_html_table_rows(bg_color=current_bg_color)
        return f"<table>{result}</table>"

    def __parse(self, bank_str):
        # split by section
        section_strs = re.split(r"\n\s*(?:SECTION:|SLACK:|EMPTY)", bank_str.strip())
        # abbreviated bank name
        bank_name = re.sub(r'^(\S+)(?: Bank #(\S+))?.*$', r'\1\2', section_strs[0].strip()).rstrip(':')
        # parse remainder of sections
        sections = [RGBASMMapSection(section_str) for section_str in section_strs[1:-1]]
        # sort ascending
        sections.sort(key=lambda section: section.start)
        return bank_name, sections

    def __get_size(self):
        # based on first letter of bank name
        return {'R' : 0x4000,  # ROM0/ROMX
                'V' : 0x2000,  # VRAM
                'S' : 0x2000,  # SRAM
                'W' : 0x2000 if self.wram_single_bank else 0x1000,  # WRAM
                'O' : 0x00A0,  # OAM
                'H' : 0x007F }.get(self.name[0])  # HRAM

    def __get_start_address(self):
        # based on bank name
        if self.name == "ROM0":
            return 0x0000  # ROM0
        if self.name == "WRAM0":
            return 0xC000  # WRAM0
        return {'R' : 0x4000,  # ROMX
                'V' : 0x8000,  # VRAM
                'S' : 0xA000,  # SRAM
                'W' : 0xD000,  # WRAMX
                'O' : 0xFE00,  # OAM
                'H' : 0xFF80 }.get(self.name[0])  # HRAM

    PALETTES = {
        'red'    : ((103,  0, 13),(165, 15, 21),(203, 24, 29),
                    (239, 59, 44),(251,106, 74),(251,106, 74),
                    (252,187,161),(254,224,210),(255,245,240)),
        'orange' : ((127, 39,  4),(166, 54,  3),(217, 72,  1),
                    (241,105, 19),(253,141, 60),(253,174,107),
                    (253,208,162),(254,230,206),(255,245,235)),
        'yellow' : ((102, 37,  6),(153, 52,  4),(204, 76,  2),
                    (236,112, 20),(254,153, 41),(254,196, 79),
                    (254,227,145),(255,247,188),(255,255,229)),
        'green'  : ((  0, 68, 27),(  0,109, 44),( 35,139, 69),
                    ( 65,171, 93),(116,196,118),(161,217,155),
                    (199,233,192),(229,245,224),(247,252,245)),
        'blue'   : ((  8, 48,107),(  8, 81,156),( 33,113,181),
                    ( 66,146,198),(107,174,214),(158,202,225),
                    (198,219,239),(222,235,247),(247,251,255)),
        'purple' : (( 63,  0,125),( 84, 39,143),(106, 81,163),
                    (128,125,186),(158,154,200),(188,189,220),
                    (218,218,235),(239,237,245),(252,251,253))
    }
    def __get_color_palette(self):
        # to use for svg visualization
        if self.name == "ROM0":
            return self.PALETTES['red']         # ROM0
        return {'R' : self.PALETTES['orange'],  # ROMX
                'V' : self.PALETTES['yellow'],  # VRAM
                'S' : self.PALETTES['green'],   # SRAM
                'W' : self.PALETTES['blue']     # WRAM
                }.get(self.name[0], self.PALETTES['purple'])  # OAM/HRAM


class RGBASMMapSection:
    """
    Parse a single section string into its name, start and end address, and list of sublocation tuples (addr, name)
    """
    def __init__(self, section_str):
        self.start, self.end, self.name, self.sublocations = self.__parse(section_str)

    def __len__(self):
        return self.end - self.start

    def to_html_table_rows(self, bg_color=(255,255,255)):
        # return as table row element(s)
        text_color = 'black' if sum(bg_color)/3 > 127 else 'white'
        if len(self) > 0:
            result = f'<tr><th style="color:{text_color};background-color:rgb{bg_color};">${self.start:04X}&ndash;${self.end:04X}</th><th>{self.name}</th></tr>'
        else:
            result = f'<tr><th style="color:{text_color};background-color:rgb{bg_color};">${self.start:04X}</th><th>{self.name}</th></tr>'
        for sublocation in self.sublocations:
            result += f'<tr><td>${sublocation[0]:04X}</td><td>{sublocation[1]}</td></tr>'
        return result

    def __parse(self, section_str):
        # split section into locations/location ranges
        location_strs = section_str.strip().split('\n')
        # head has range and name
        section_head_parsed = re.match(r'(\$....(?:\-\$....)?)[^\[]+(?:\["(.*)"\])$', location_strs[0])
        section_range, section_name = section_head_parsed.groups()

        if len(section_range) == 5:
            # single address means the same start and end
            section_range = section_range + '-' + section_range
        # convert hex range to start/end ints
        start_addr, end_addr = int(section_range[1:5], 16), int(section_range[7:11], 16)

        sublocations = []
        for sublocation_str in location_strs[1:]:
            sublocation_parsed = re.match(r'(\$....) = (.*)$', sublocation_str.strip())
            subloc_addr_str, subloc_name = sublocation_parsed.groups()
            subloc_addr = int(subloc_addr_str[1:], 16)
            sublocations.append((subloc_addr, subloc_name))

        sublocations.sort()

        return start_addr, end_addr, section_name, sublocations


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('inf_name', help="input filename (with or without .asm extension)")
    parser.add_argument('-w', help="single WRAM bank mode (see rgblink -w)", action="store_true")
    main(parser.parse_args())
