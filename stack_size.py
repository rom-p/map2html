#!/usr/bin/env python3

'''
this script attempts to calculate max stack size used by the firmware.

it relies on *.ci files produced by the compiler (use `-fcallgraph-info=da,su` parameter for gcc)

** The approach is very much flawed: **
1. it currently is unable to include the ASM functions
2. see the rest of the problems in TODO below
'''

from pathlib import Path
import re

# TODO:
# 1. find a way to get the callgraph-info from `.S` files (the gcc ignores the flags for assembler)
# 2. consume the list of entry points (currently hardcoded)  Since this script is running before linking (BTW, can we change that???) -- we don't know what functions will be included in the final binary
# 3. adjustable size of stack frame
# 4. how to deal with indirect calls?
# 5. count the heap as well (separately, of course)


ROOT = '.obj'
FILE_MASK = '*.ci'
nodes = {}   # key: function, value: local bytes
edges = {}   # key: function, value: list of functions called

entry_points = [ # first, hacks: since we can't get stack usage data from assembly (fix it!!!), this hack gets it from the first C functions in each path
                '_start', 'SystemInit', 'NMI_HandlerC', 'HardFault_HandlerC',
                # below are standard core vectors
                'Reset_Handler', 'NMI_Handler', 'HardFault_Handler', 'SVC_Handler',
                'PendSV_Handler', 'SysTick_Handler',
                # below are standard device interrupts
                'BLE_WAKEUP_LP_Handler', 'rwble_isr', 'UART_Handler', 'UART2_Handler',
                'I2C_Handler', 'SPI_Handler', 'ADC_Handler', 'KEYBRD_Handler',
                'BLE_RF_DIAG_Handler', 'RFCAL_Handler', 'GPIO0_Handler', 'GPIO1_Handler',
                'GPIO2_Handler','GPIO3_Handler', 'GPIO4_Handler', 'SWTIM_Handler',
                'WKUP_QUADEC_Handler', 'SWTIM1_Handler', 'RTC_Handler', 'DMA_Handler',
                'XTAL32M_RDY_Handler', 'RESERVED21_Handler', 'RESERVED22_Handler', 'RESERVED23_Handler']

print_edges = False


def getSubtreeDepth(fx):
    max_depth = 0
    deepest_path = ''
    if fx in edges:
        for callee in edges[fx]:
            depth, path = getSubtreeDepth(callee)
            if depth > max_depth:
                max_depth = depth
                deepest_path = path
    return max_depth + nodes[fx], fx + ', ' + deepest_path


for file in list(Path(ROOT).rglob(FILE_MASK)):
    with open(file) as f:
        for line in list(f):
            body = line[line.find('{')+1:line.find('}')].strip()
            parts = re.split(''' (?=(?:[^'"]|'[^']*'|"[^"]*")*$)''', body)
            if line.startswith('node:'):
                title = parts[1].strip('"')
                label = parts[3].strip('"')
                bytes = re.search('''(\d+) bytes \(static\)''', label)
                bytes_used = 0
                if bytes:
                    bytes_used = int(bytes.group(1))
                nodes[title] = 8 + bytes_used
            elif line.startswith('edge:'):
                source = parts[1].strip('"')
                target = parts[3].strip('"')
                if source not in edges:
                    edges[source] = []
                edges[source].append(target)

entry_point_depths = {}
entry_point_paths = {}
max_depth = 0
deepest_path = ''
for fx, _ in nodes.items():
    depth, path = getSubtreeDepth(fx)
    if depth > max_depth:
        max_depth = depth
        deepest_path = path
    if fx in entry_points:
        entry_point_depths[fx] = depth
        entry_point_paths[fx] = path
if print_edges:
    for fx, edge in edges.items():
        print("%s -> %s" % (fx, edge))
print("max depth is %s:  %s" % (max_depth, deepest_path))
for ep in entry_points:
    if ep in entry_point_depths:
        print("%s depth is %s:  %s" % (ep, entry_point_depths[ep], entry_point_paths[ep].strip(', ')))
    else:
        print("%s -- unknown depth" % ep)
