"""
Various usefull conversions for the LP system
"""


def bytereverse(value):
    """ 
    Byte reverses data
    """
    bytearray = []
    for i in xrange(0, len(value)):
        if i % 2 == 1:
            bytearray.append(value[i-1:i+1])
    return "".join(bytearray[::-1])

def wordreverse(in_buf):
    """
    Does a word based reverse
    """
    out_words = []
    for i in range(0, len(in_buf), 4):
        out_words.append(in_buf[i:i+4])
    out_words.reverse()
    out_buf = ""
    for word in out_words:
        out_buf += word
    return out_buf

def extract_block(response):
    """
    Extracts the block from the LP
    """
    data = response['result']['data']
    block = data.decode('hex')[0:64]
    block = wordreverse(block)
    block = block.encode('hex')[56:120]
    
    return block
