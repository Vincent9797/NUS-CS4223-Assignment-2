from cache import Block
from copy import deepcopy

class Bus():
    def __init__(self, caches):
        self.caches = caches
        for i in self.caches:
            i.bus = self

        self.traffic = 0
        self.invalidations = 0
        self.private_access = 0
        self.public_access = 0

    def mesi_read(self, id, tag, set, offset):
        block = None
        for cache in self.caches[:id] + self.caches[id+1:]: # check for valid block in other cache
            index = cache.in_cache(tag, set, offset)
            if index>=0:
                block = cache.data[set][index]
                if block.state == 'M':
                    self.private_access += 1
                elif block.state == 'E':
                    self.public_access += 1
                elif block.state == 'S':
                    self.public_access += 1

                block.state = 'S'

        self.traffic += cache.block_size
        if block != None:
            return deepcopy(block), 2
        else:
            new_block = Block(cache.num_words, 'E')
            new_block.tag = tag
            return new_block, 100


    def mesi_readx(self, id, tag, set, offset): # wants to write but do not have block = request for block from others
        block = None
        for cache in self.caches[:id] + self.caches[id+1:]: # check for valid block in other cache
            index = cache.in_cache(tag, set, offset)
            if index>=0:
                block = cache.data[set][index]
                if block.state == 'M':
                    self.private_access += 1
                elif block.state == 'E':
                    self.public_access += 1
                elif block.state == 'S':
                    self.public_access += 1

                block.state = 'I'

        self.traffic += cache.block_size

        if block != None:
            self.invalidations += 1
            return deepcopy(block), 2
        else:
            new_block = Block(cache.num_words, 'M')
            new_block.tag = tag
            return new_block, 100

    def mesi_upgr(self, id, tag, set, offset):
        for cache in self.caches[:id] + self.caches[id+1:]: # check for valid block in other cache
            index = cache.in_cache(tag, set, offset)
            if index>=0:
                cache.data[set][index].state = 'I'
                del cache.lru[set][cache.data[set][index]]
        self.invalidations += 1

    def mesi_flush(self, id, tag, set, offset):
        self.traffic += self.caches[0].block_size  # update main memory

    def dragon_read(self, id, tag, set, offset):
        block = None
        for cache in self.caches[:id] + self.caches[id+1:]: # check for valid block in other cache
            index = cache.in_cache(tag, set, offset)
            if index>=0:
                block = cache.data[set][index]
                if block.state == 'Sm':
                    self.public_access += 1
                    self.dragon_flush(id, tag, set, offset)
                elif block.state == 'Sc':
                    self.public_access += 1
                elif block.state == 'E':
                    self.public_access += 1
                    block.state = 'Sc'
                    self.shared.add(block)
                elif block.state == 'M':
                    self.private_access += 1
                    block.state = 'Sm'
                    self.shared.add(block)
                    self.dragon_flush(id, tag, set, offset)


        self.traffic += cache.block_size
        if block != None:
            new_block = deepcopy(block)
            new_block.state = 'Sc'
            self.shared.add(new_block)
            return new_block, 2
        else:
            new_block = Block(cache.num_words, 'E')
            new_block.tag = tag
            return new_block, 100

    def dragon_update(self, id, tag, set, offset):
        block = None
        for cache in self.caches[:id] + self.caches[id+1:]: # check for valid block in other cache
            index = cache.in_cache(tag, set, offset)
            if index>=0:
                block = cache.data[set][index]
                if block.state == 'Sm':
                    self.public_access += 1
                    block.state = 'Sc'
                elif block.state == 'Sc':
                    self.public_access += 1
                elif block.state == 'E':
                    self.public_access += 1
                elif block.state == 'M':
                    self.private_access += 1

        self.traffic += cache.block_size
        if block != None:
            new_block = deepcopy(block)
            new_block.state = 'Sc'
            self.shared.add(new_block)
            return new_block, 2
        else:
            new_block = Block(cache.num_words, 'E')
            new_block.tag = tag
            return new_block, 100

    def dragon_flush(self, id, tag, set, offset):
        self.traffic += self.caches[0].block_size

    def report(self):
        print('===== REPORT FOR BUS =====')
        print('Data Traffic (Bytes):', self.traffic)
        print('Invalidations:', self.invalidations)
        print('Access to Private Data:', self.private_access/(self.private_access + self.public_access))
        print('Access to Public Data:', self.public_access / (self.private_access + self.public_access))
