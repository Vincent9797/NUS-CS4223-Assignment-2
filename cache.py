"""
implementation of write-back, write-allocate policy
direct mapping
4KB, 2-way set-associative cache
"""
from collections import defaultdict, OrderedDict
from math import log

class Block:
    def __init__(self, num_words, state='I'):
        self.state = state
        self.tag = None
        self.words = [None] * num_words

    def __str__(self):
        return str(self.tag) + " " + self.state

    def __repr__(self):
        return str(self.tag) + " " + self.state

class Cache:
    def __init__(self, id, cache_size, associativity, block_size, word_size):
        self.cache_hit = 0
        self.cache_miss = 0
        self.lru = defaultdict(OrderedDict)

        self.id = id
        self.cache_size = cache_size
        self.associativity = associativity
        self.block_size = block_size # in bytes
        self.word_size = word_size # in bits

        self.num_sets = self.cache_size // (self.block_size*self.associativity)
        self.num_words = self.block_size // (self.word_size//8)
        self.data = {}
        for i in range(self.num_sets):
            self.data[i] = {}
            for j in range(self.associativity):
                self.data[i][j] = Block(self.num_words)

    # makes more sense to be in processor class
    def process_address(self, memory_address):
        memory_address = memory_address[2:]
        memory_address = '0' * (8 - len(memory_address)) + memory_address  # in hex
        memory_address = bin(int(memory_address, 16))[2:]
        memory_address = '0' * (32 - len(memory_address)) + memory_address  # in hex

        num_bits_for_offset = int(log(self.block_size)/log(2))
        num_bits_for_setindex = int(log(self.num_sets)/log(2))

        tag = int(memory_address[:-num_bits_for_offset-num_bits_for_setindex], 2)
        set = int(memory_address[-num_bits_for_offset-num_bits_for_setindex:-num_bits_for_offset], 2)
        offset = int(memory_address[-num_bits_for_offset:], 2)
        return tag, set, offset

    def in_cache(self, tag, set_index, offset):
        for index, i in enumerate(self.data[set_index].values()):
            if i.state != 'I' and i.tag == tag:
                return index
        return -1

    def cache_line_full(self, tag, set_index, offset):
        for index, i in enumerate(self.data[set_index].values()):
            if i.state == 'I':
                return index
        return -1

class MESICache(Cache):
    def __init__(self, id, cache_size, associativity, block_size, word_size):
        super().__init__(id, cache_size, associativity, block_size, word_size)

    def load(self, memory_address):
        tag, set, offset = self.process_address(memory_address)

        index = self.in_cache(tag, set, offset)
        if index >= 0:
            self.cache_hit += 1

            # update LRU
            if set in self.lru:
                self.lru[set].move_to_end(self.data[set][index], last=True)
            else:
                self.lru[set][self.data[set][index]] = 1
            return 1
        else:
            self.cache_miss += 1

            first_invalid = self.cache_line_full(tag, set, offset)
            if first_invalid == -1: # no invalid blocks found = cache line full
                block, _ = self.lru[set].popitem(last=False)
                if block.state == 'M':
                    self.bus.mesi_flush(self.id, tag, set, offset)
                block.state = 'I'

            block, cycle = self.bus.mesi_read(self.id, tag, set, offset) # request for block from the bus
            for i in range(self.associativity):
                if self.data[set][i].state == 'I':
                    self.data[set][i] = block
                    self.lru[set][block] = 1
                    break
            return cycle # could be 2 or 100 depending on whether it is in other cache

    def store(self, memory_address):
        tag, set, offset = self.process_address(memory_address)

        index = self.in_cache(tag, set, offset)
        if index>=0: # write hit
            self.cache_hit += 1
            if self.data[set][index].state == 'S':
                self.bus.mesi_upgr(self.id, tag, set, offset)
            self.data[set][index].state = 'M'
            return 1
        else:
            self.cache_miss += 1

            first_invalid = self.cache_line_full(tag, set, offset)
            if first_invalid == -1:
                block, _ = self.lru[set].popitem(last=False)
                if block.state == 'M':
                    self.bus.mesi_flush(self.id, tag, set, offset)
                    self.bus.traffic += self.block_size # update main memory
                block.state = 'I'

            block, cycle = self.bus.mesi_readx(self.id, tag, set, offset) # request for the block
            block.state = 'M'

            for i in range(self.associativity):
                if self.data[set][i].state == 'I':
                    self.data[set][i] = block
                    self.lru[set][block] = 1
                    break
            return cycle

class DragonCache(Cache):
    def __init__(self, id, cache_size, associativity, block_size, word_size):
        super().__init__(id, cache_size, associativity, block_size, word_size)

    def load(self, memory_address):
        tag, set, offset = self.process_address(memory_address)

        associativity = self.in_cache(tag, set, offset)
        if associativity >= 0:
            self.cache_hit += 1

            # update LRU
            if set in self.lru:
                self.lru[set].move_to_end(self.data[set][associativity], last=True)
            else:
                self.lru[set][associativity] = 1
            return 1
        else:
            self.cache_miss += 1

            first_invalid = self.cache_line_full(tag, set, offset)
            if first_invalid == -1: # no invalid blocks found = cache line full
                block, _ = self.lru[set].popitem(last=False)
                block.state = 'I'

            block, cycle = self.bus.dragon_read(self.id, tag, set, offset) # request for block from the bus
            for i in range(self.associativity):
                if self.data[set][i].state == 'I':
                    self.data[set][i] = block
                    self.lru[set][block] = 1
                    break
            return cycle # could be 2 or 100 depending on whether it is in other cache

    def store(self, memory_address):
        tag, set, offset = self.process_address(memory_address)

        index = self.in_cache(tag, set, offset)
        if index>=0: # write hit
            self.cache_hit += 1

            block = self.data[set][index]
            if block.state == 'Sm':
                block.state = 'M'
                if block in self.bus.shared:
                    self.bus.dragon_update(self.id, tag, set, offset)
            elif block.state == 'E':
                block.state = 'M'
            elif block.state == 'Sc':
                if block in self.bus.shared:
                    self.bus.dragon_update(self.id, tag, set, offset)
                    block.state = 'Sm'
                else:
                    block.state = 'M'
            self.data[set][index].state = 'M'
            return 1
        else:
            self.cache_miss += 1

            first_invalid = self.cache_line_full(tag, set, offset)
            if first_invalid == -1:
                block, _ = self.lru[set].popitem(last=False)
                if block.state == 'M':
                    self.bus.traffic += self.block_size # update main memory
                block.state = 'I'

            block, cycle = self.bus.dragon_read(self.id, tag, set, offset) # request for the block
            if block in self.bus.shared:
                block.state = 'Sm'
            else:
                block.state = 'M'

            for i in range(self.associativity):
                if self.data[set][i].state == 'I':
                    self.data[set][i] = block
                    self.lru[set][block] = 1
                    break
            return cycle