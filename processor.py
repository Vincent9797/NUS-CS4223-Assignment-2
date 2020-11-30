from cache import Cache

class Processor():
    def __init__(self, id, instructions, cache, bus):
        self.cycle = 0
        self.compute_cycle = 0
        self.loads = 0
        self.stores = 0

        self.id = id # 0-3
        self.instructions = open(instructions).read().splitlines()
        self.line_num = 0  # line of instruction
        self.still_executing = True
        self.length_instructions = len(self.instructions)
        self.cache = cache

    def execute(self, curr_cycle):
        if curr_cycle != self.cycle:
            return

        if self.line_num < self.length_instructions:
            self.process(self.instructions[self.line_num])
            self.line_num += 1
        else:
            self.still_executing = False

    def process(self, trace):
        label, value = trace.split(' ')
        if label == '0':
            self.loads += 1
            self.cycle += self.load(value)
        elif label == '1':
            self.stores += 1
            self.cycle += self.store(value)
        elif label == '2':
            tmp = int(value, 0)
            self.cycle += tmp
            self.compute_cycle += tmp

    def load(self, memory_address):
        return self.cache.load(memory_address)

    def store(self, memory_address):
        return self.cache.store(memory_address)

    def report(self):
        print('===== REPORT FOR PROCESSOR', self.id, ' =====')
        print('Execution Cycles:', self.cycle)
        print('Compute Cycles:', self.compute_cycle)
        print('Load Operations:', self.loads)
        print('Store Operations:', self.stores)
        print('Idle Cycles:', self.cycle - self.compute_cycle)
        print('Cache Miss Rate:', self.cache.cache_miss / (self.cache.cache_miss+self.cache.cache_hit))
        print('\n')