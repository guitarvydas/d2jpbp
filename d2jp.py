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
            print (" " * self.indent, end="", file=sys.stderr)
            print (self.prefix, end="", file=sys.stderr)
        pass

    
buffer = StringBuffer ()
indent = Indentation ()

def parse_debug_prefix (s):
    global indent
    indent.prefix = s

def pbuffrepr (s):
    global buffer
    print (f'{s}{buffer.buffrepr()}', file=sys.stderr)
    
def fail (s):
    global buffer
    global indent
    indent.out ()
    indent.pr ()
    if debugtrace:
        print (f'fail {s}', file=sys.stderr)
    buffer.rewind ()
    return False

def begin (s):
    global buffer
    global indent
    indent.pr ()
    indent.ind ()
    if debugprogress:
        print (f'begin {s} {buffer.buffrepr()}', file=sys.stderr)
    elif debugtrace:
        print (f'begin {s}', file=sys.stderr)
    buffer.push_mark ()

def accept (s):
    global buffer
    global indent
    indent.out ()
    indent.pr ()
    prev = buffer.pop_mark ()
    if debugprogress or debugtrace:
        print (f'accept {s}', file=sys.stderr)
    return True

def debug (name, s):
    global buffer
    indent.pr ()
    indent.ind ()
    if debugprogress:
        print (f'{name} {s} {buffer.buffrepr()}', file=sys.stderr)
    elif debugtrace:
        print (f'{name} {s}', file=sys.stderr)

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



target = []
more = []
logicalop = []

def stkpush (stk, val):
    stk.append (val)

def stkpop (stk):
    stk.pop ()

def stktop (stk):
    return stk [-1]


### SeqGroup part - handles chain of Stepper or SeqGroup parts
def SeqGroup_handler (eh, mev):
    global target, more, logicalop,  buffer
    if mev.port == "":
        stkpush (more, "") ; stkpush (logicalop, "and") ; eh.instance_data = "triggered"
        zd.send (eh, "tick", "", mev)
    elif mev.port == "done":
        stkpop (more) ; stkpop (logicalop)
        zd.send (eh, "", mev.payload.v, mev)
    else:
        raise Exception (f'internal error in SeqGroup_handler port={mev.port} payload={mev.payload.v}')

def SeqGroup_reset_handler (eh):
    global target, more, logicalop
    if eh.instance_data == "triggered":
        stkpop (more) ; stkpop (logicalop)
        eh.instance_data = None

def SeqGroup_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "SeqGroup")
    return zd.make_leaf ( name_with_id, owner, None, arg, SeqGroup_handler, SeqGroup_reset_handler)

def SeqGroup_install (reg):
    zd.register_component (reg, zd.mkTemplate ("SeqGroup", None, SeqGroup_instantiate))

### AltGroup part - handles chain of Stepper or AltGroup parts
def AltGroup_handler (eh, mev):
    global target, more, logicalop
    if mev.port == "":
        stkpush (more, "not") ; stkpush (logicalop, "or") ; eh.instance_data = "triggered"
        zd.send (eh, "tick", "", mev)
    elif mev.port == "done":
        stkpop (more) ; stkpop (logicalop)
        zd.send (eh, "", mev.payload.v, mev)
    else:
        raise Exception (f'internal error in AltGroup_handler port={mev.port} payload={mev.payload.v}')

def AltGroup_reset_handler (eh):
    global target, more, logicalop
    if eh.instance_data == "triggered":
        stkpop (more) ; stkpop (logicalop)
        eh.instance_data = None

def AltGroup_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "AltGroup")
    return zd.make_leaf ( name_with_id, owner, None, arg, AltGroup_handler, AltGroup_reset_handler)

def AltGroup_install (reg):
    zd.register_component (reg, zd.mkTemplate ("AltGroup", None, AltGroup_instantiate))



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

def InitBuffer_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Initialize Buffer", None, InitBuffer_instantiate))

### TF - input a boolean value, fire T output with true if input is true, else fire F output with false
def TF_handler (eh, mev):
    if mev.port == "":
        if mev.payload.v == "true":
            zd.send (eh, "T", "true", mev)
        else:
            zd.send (eh, "F", "false", mev)
    else:
        raise Exception (f'internal error in TF_handler port={mev.port} payload={mev.payload.v}')

def TF_reset_handler (eh):
    pass

def TF_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "TF")
    return zd.make_leaf ( name_with_id, owner, None, arg, TF_handler, TF_reset_handler)

def TF_install (reg):
    zd.register_component (reg, zd.mkTemplate ("TF", None, TF_instantiate))


    
### Parse an "a" from the buffer
def ParseA_handler (eh, mev):
    global myid, targetid, more, logicalop
    if mev.port == "":
        bool = parse_string ("a")
        zd.send (eh, "", str (bool), mev)
    else:
        raise Exception (f'internal error in ParseA_handler port={mev.port} payload={mev.payload.v}')

def ParseA_reset_handler (eh):
    pass

def ParseA_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "ParseA")
    return zd.make_leaf ( name_with_id, owner, None, arg, ParseA_handler, ParseA_reset_handler)

def ParseA_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Parse A", None, ParseA_instantiate))

### Parse a "b" from the buffer
def ParseB_handler (eh, mev):
    global myid, targetid, more, logicalop
    if mev.port == "":
        bool = parse_string ("b")
        zd.send (eh, "", str (bool), mev)
    else:
        raise Exception (f'internal error in ParseB_handler port={mev.port} payload={mev.payload.v}')

def ParseB_reset_handler (eh):
    pass

def ParseB_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "ParseB")
    return zd.make_leaf ( name_with_id, owner, None, arg, ParseB_handler, ParseB_reset_handler)

def ParseB_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Parse B", None, ParseB_instantiate))
