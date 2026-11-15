import sys
import kernel0d as zd

######################################################
## Global String Buffer and builtin parsing primitives
######################################################

debugprogress = False
debugtrace = False

def declare (bool):
    return bool

class StringBuffer ():
    def __init__ (self):
        self.buff = ""
        self.bx = 0
        self.marks = []
    def set_input (self, s):
        self.buff = s
    def push_mark (self):
        self.marks.append (self.bx)
    def pop_mark (self):
        self.marks.pop ()
    def rewind (self):
        self.bx = self.marks.pop ()
    def accept_char (self):
        self.bx += 1
    def empty (self):
        return self.bx >= len (self.buff)
    def is_space (self):
        if self.empty ():
            return False
        elif self.buff [self.bx] == " " or self.buff [self.bx] == "," or self.buff [self.bx] == "\n" or self.buff [self.bx] == "\t" :
            return True
    def look (self):
        if self.empty ():
            raise Exception ('look called on empty input buffer')
        else:
            return self.buff [self.bx]
    def buffrepr (self):
        return f"<{self.bx}>{self.buff[self.bx:10].replace('\n', '⤶').replace(' ', '␣').replace('\t', '⇢')}"
    def parse_char (self, c):
        if self.empty ():
            return False
        if c == self.buff [self.bx]:
            self.accept_char ()
            return True
        return False

class Indentation ():
    def __init__ (self):
        self.indent = 0
        self.prefix = ''
    def ind (self):
        self.indent += 1
    def out (self):
        self.indent -= 1
    def pr (self):
        if debugprogress or debugtrace:
            print (" " * self.indent, end="")
            print (self.prefix, end="")
        pass

    
buffer = StringBuffer ()
indent = Indentation ()

def parse_debug_prefix (s):
    global indent
    indent.prefix = s

def pbuffrepr (s):
    global buffer
    print (f'{s}{buffer.buffrepr()}')
    
def fail (s):
    global buffer
    global indent
    indent.out ()
    indent.pr ()
    if debugtrace:
        print (f'fail {s}')
    buffer.rewind ()
    return False

def begin (s):
    global buffer
    global indent
    indent.pr ()
    indent.ind ()
    if debugprogress:
        print (f'begin {s} {buffer.buffrepr()}')
    elif debugtrace:
        print (f'begin {s}')
    buffer.push_mark ()

def accept (s):
    global buffer
    global indent
    indent.out ()
    indent.pr ()
    prev = buffer.pop_mark ()
    if debugprogress or debugtrace:
        print (f'accept {s}')
    return True

def debug (name, s):
    global buffer
    indent.pr ()
    indent.ind ()
    if debugprogress:
        print (f'{name} {s} {buffer.buffrepr()}')
    elif debugtrace:
        print (f'{name} {s}')

def parse_string (s):
    global buffer
    i = 0
    debug ("parse_string", s)
    while i < len (s):
        if buffer.parse_char (s [i]):
            i += 1
            continue
        else:
            return False
    return True

def any ():
    global buffer
    debug ("any", "_")
    if buffer.empty ():
        return False
    else:
        buffer.accept_char ()
        return True
    
def parse_upto (c):
    global buffer
    while True:
        if buffer.empty ():
            return False
        else:
            if c == buffer.look ():
                break
            else:
                buffer.accept_char ()
    return True

def parse_range (first, last):
    global buffer
    if buffer.look () >= first and buffer.look () <= last:
        buffer.accept_char ()
        return True
    else:
        return False

def parse_ignoring (f):
    global buffer
    debug ("ignore", "")
    while (buffer.is_space ()):
        buffer.accept_char ()
    r = f ()
    while (buffer.is_space ()):
        buffer.accept_char ()
    return r

def parse_one_or_more (f):
    parse_debug_prefix ('+')
    if f ():
        while True:
            if f ():
                continue
            else:
                parse_debug_prefix ('')
                return True
    else:
        parse_debug_prefix ('')
        return False
    
def parse_either (flist):
    parse_debug_prefix ('|')
    while True:
        f = flist [0]
        if f ():
            parse_debug_prefix ('')
            return True
        elif flist:
            if len (flist) > 1:
                flist = flist [1:]
            else:
                parse_debug_prefix ('')
                return False
        else:
            parse_debug_prefix ('')
            return False
    raise Exception ("internal error: should not have reached this point")

def parse_set_input (s):
    buffer.set_input (s)





########## PBP Parts #############

### Predicate that parses "a" ###
def Preda_handler (eh, mev):
    zd.send (eh, "out", str(parse_string ("a")), mev)

def Preda_reset_handler (eh):
    pass


def Preda_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "Predicate a")
    return zd.make_leaf ( name_with_id, owner, None, arg, Preda_handler, Preda_reset_handler)

# define template
def Preda_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Preda", None, Preda_instantiate))

### Predicate that parses b" ###
def Predb_handler (eh, mev):
    zd.send (eh, "out", str(parse_string ("b")), mev)

def Predb_reset_handler (eh):
    pass

def Predb_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "Predicate b")
    return zd.make_leaf ( name_with_id, owner, None, arg, Predb_handler, Predb_reset_handler)

# define template
def Predb_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Predb", None, Predb_instantiate))


### PredItem part - invokes Preda or Predb (per schematic) ###
def PredItem_handler (eh, mev):
    if mev.port== "in":
        zd.send (eh, "target", mev.payload.v, mev)
    elif mev.port == "target":
        zd.send (eh, "out", mev.payload.v, mev)
    else:
        raise Exception ("internal error in PredItem_handler")

def PredItem_reset_handler (eh):
    pass

def PredItem_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "PredItem")
    return zd.make_leaf ( name_with_id, owner, None, arg, PredItem_handler, PredItem_reset_handler)

# define template
def PredItem_install (reg):
    zd.register_component (reg, zd.mkTemplate ("PredItem", None, PredItem_instantiate))


### AltItem part - handles one step of alternation
def AltItem_handler (eh, mev):
    if mev.port == "in":
        zd.send (eh, "target", mev.payload.v, mev)
    elif mev.port == "target":
        zd.send (eh, "out", mev.payload.v, mev)
    else:
        raise Exception ("internal error in AltItem_handler")

def AltItem_reset_handler (eh):
    pass

def AltItem_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "AltItem")
    return zd.make_leaf ( name_with_id, owner, None, arg, AltItem_handler, AltItem_reset_handler)

# define template
def AltItem_install (reg):
    zd.register_component (reg, zd.mkTemplate ("AltItem", None, AltItem_instantiate))

    
### AltGroup part - handles alternation chain of AltItems
def AltGroup_handler (eh, mev):
    if mev.port == "in":
        zd.send (eh, "target", mev.payload.v, mev)
    elif mev.port == "target":
        zd.send (eh, "out", mev.payload.v, mev)
    else:
        raise Exception ("internal error in AltGroup_handler")

def AltGroup_reset_handler (eh):
    pass

def AltGroup_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "AltGroup")
    return zd.make_leaf ( name_with_id, owner, None, arg, AltGroup_handler, AltGroup_reset_handler)

# define template
def AltGroup_install (reg):
    zd.register_component (reg, zd.mkTemplate ("AltGroup", None, AltGroup_instantiate))

    
### SeqGroup part - handles chain of SeqItem/PredItem/AltGroup
def SeqGroup_handler (eh, mev):
    if mev.port == "in":
        zd.send (eh, "target", mev.payload.v, mev)
    elif mev.port == "target":
        zd.send (eh, "out", mev.payload.v, mev)
    else:
        raise Exception (f'internal error in SeqGroup_handler port={mev.port} payload={mev.payload.v}')

def SeqGroup_reset_handler (eh):
    pass

def SeqGroup_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "SeqGroup")
    return zd.make_leaf ( name_with_id, owner, None, arg, SeqGroup_handler, SeqGroup_reset_handler)

# define template
def SeqGroup_install (reg):
    zd.register_component (reg, zd.mkTemplate ("SeqGroup", None, SeqGroup_instantiate))


### Initialize Buffer part - starts the parser by storing the string mev.payload.v into the buffer
def InitBuffer_handler (eh, mev):
    if mev.port == "":
        parse_set_input (mev.payload.v)
        zd.send (eh, "", "", mev)
    else:
        raise Exception (f'internal error in InitBuffer_handler port={mev.port} payload={mev.payload.v}')

def InitBuffer_reset_handler (eh):
    pass

def InitBuffer_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "InitBuffer")
    return zd.make_leaf ( name_with_id, owner, None, arg, InitBuffer_handler, InitBuffer_reset_handler)

# define template
def InitBuffer_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Initialize Buffer", None, InitBuffer_instantiate))

    
