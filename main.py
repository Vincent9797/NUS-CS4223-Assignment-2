import argparse
from processor import Processor
from bus import Bus
from cache import MESICache, DragonCache
from pprint import pprint

def main():
    parser = argparse.ArgumentParser(description='Cache Coherence')
    parser.add_argument('-protocol')
    parser.add_argument('-input_file')
    parser.add_argument('-cache_size')
    parser.add_argument('-associativity')
    parser.add_argument('-block_size')
    parser.add_argument('-word_size')

    args = parser.parse_args()
    args.cache_size = int(args.cache_size)
    args.associativity = int(args.associativity)
    args.block_size = int(args.block_size)
    args.word_size = int(args.word_size)

    if args.protocol == 'MESI':
        c0 = MESICache(0, args.cache_size, args.associativity, args.block_size, args.word_size)
        c1 = MESICache(1, args.cache_size, args.associativity, args.block_size, args.word_size)
        c2 = MESICache(2, args.cache_size, args.associativity, args.block_size, args.word_size)
        c3 = MESICache(3, args.cache_size, args.associativity, args.block_size, args.word_size)
    elif args.protocol == 'Dragon':
        c0 = DragonCache(0, args.cache_size, args.associativity, args.block_size, args.word_size)
        c1 = DragonCache(1, args.cache_size, args.associativity, args.block_size, args.word_size)
        c2 = DragonCache(2, args.cache_size, args.associativity, args.block_size, args.word_size)
        c3 = DragonCache(3, args.cache_size, args.associativity, args.block_size, args.word_size)

    bus = Bus([c0, c1, c2, c3])
    if args.protocol == 'Dragon':
        bus.shared = set()

    p0 = Processor(0, args.input_file + '_0.DATA', c0, bus)
    p1 = Processor(1, args.input_file + '_1.DATA', c1, bus)
    p2 = Processor(2, args.input_file + '_2.DATA', c2, bus)
    p3 = Processor(3, args.input_file + '_3.DATA', c3, bus)

    cond = any([i.still_executing for i in [p0, p1, p2, p3]])
    cycle = 0
    while cond:
        p0.execute(cycle)
        # pprint(c0.data)
        p1.execute(cycle)
        # pprint(c1.data)
        p2.execute(cycle)
        # pprint(c2.data)
        p3.execute(cycle)
        # pprint(c3.data)
        cond = any([i.still_executing for i in [p0, p1, p2, p3]])
        cycle += 1

    print('===== END OF EXECUTION =====')
    print('Overall Execution Cycle:', max([p0.cycle, p1.cycle, p2.cycle, p3.cycle]))
    print('\n')

    p0.report()
    p1.report()
    p2.report()
    p3.report()

    bus.report()

if __name__ == "__main__":
    main()